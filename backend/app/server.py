"""
QuizServer implements the ChatKitServer interface for the Quiz Taker app.
Handles quiz generation via the agent and quiz.submit/quiz.reset actions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, AsyncIterator

from agents import Runner
from chatkit.agents import stream_agent_response
from chatkit.server import ChatKitServer
from chatkit.types import (
    Action,
    AssistantMessageContent,
    AssistantMessageItem,
    Attachment,
    StreamOptions,
    ThreadItemDoneEvent,
    ThreadItemReplacedEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
    WidgetItem,
)
from openai.types.responses import ResponseInputContentParam, ResponseInputTextParam

from .attachment_store import QuizAttachmentStore
from .memory_store import MemoryStore
from .quiz_agent import QuizAgentContext, quiz_agent
from .quiz_store import QuizStore
from .thread_item_converter import BasicThreadItemConverter
from .widgets.quiz_widget import QuizState, build_quiz_widget, grade_quiz, reset_quiz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuizServer(ChatKitServer[dict[str, Any]]):
    """ChatKit server for the Quiz Taker app."""

    def __init__(self) -> None:
        self.store = MemoryStore()
        self.attachment_store = QuizAttachmentStore(memory_store=self.store)
        super().__init__(self.store, attachment_store=self.attachment_store)
        self.thread_item_converter = BasicThreadItemConverter()
        self.quiz_store = QuizStore()

    async def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle widget actions like quiz.submit and quiz.reset."""
        
        logger.info(f"Received action: {action.type} with payload: {action.payload}")
        
        if action.type == "quiz.submit":
            async for event in self._handle_quiz_submit(thread, action.payload, sender, context):
                yield event
            return
        
        if action.type == "quiz.reset":
            async for event in self._handle_quiz_reset(thread, sender, context):
                yield event
            return
        
        logger.warning(f"Unknown action type: {action.type}")

    async def respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Generate a response using the quiz agent."""
        
        agent_context = QuizAgentContext(
            thread=thread,
            store=self.store,
            quiz_store=self.quiz_store,
            request_context=context,
        )

        # Load conversation history
        items_page = await self.store.load_thread_items(
            thread.id,
            after=None,
            limit=20,
            order="desc",
            context=context,
        )
        items = list(reversed(items_page.data))

        # Convert to agent input format
        input_items = await self.thread_item_converter.to_agent_input(items)

        # Run the agent
        result = Runner.run_streamed(
            quiz_agent,
            input_items,
            context=agent_context,
        )

        async for event in stream_agent_response(agent_context, result):
            yield event

    def get_stream_options(self, thread: ThreadMetadata, context: dict[str, Any]) -> StreamOptions:
        return StreamOptions(allow_cancel=False)

    async def to_message_content(self, attachment: Attachment) -> ResponseInputContentParam:
        """Convert an attachment to model input content."""
        from .file_store import file_store
        
        logger.info(f"[to_message_content] Processing attachment: {attachment.filename}, type: {attachment.content_type}")
        
        # Try to get the file data URL for the model
        if hasattr(attachment, 'id') and attachment.id:
            data_url = file_store.get_data_url(attachment.id)
            if data_url and attachment.content_type:
                # For PDFs and images, we can pass them directly
                if attachment.content_type.startswith("image/"):
                    return {
                        "type": "input_image",
                        "image_url": data_url,
                    }
        
        # For PDFs and other documents, include as text reference
        # The model will receive the file through the ChatKit SDK
        return ResponseInputTextParam(
            type="input_text",
            text=f"[User uploaded: {attachment.filename} ({attachment.content_type}). Please analyze this document to create a quiz based on its contents.]",
        )

    async def _handle_quiz_submit(
        self,
        thread: ThreadMetadata,
        payload: dict[str, Any],
        sender: WidgetItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle quiz submission - grade answers and update widget."""
        
        if not sender:
            logger.warning("quiz.submit received without sender widget")
            return
        
        logger.info(f"Payload (answers): {payload}")
        
        # Load quiz state from the quiz store
        quiz_data = self.quiz_store.load(thread.id)
        
        if not quiz_data:
            logger.error(f"Could not find quiz state for thread {thread.id}")
            return
        
        logger.info(f"Loaded quiz data: {quiz_data}")
        
        current_state = QuizState(
            title=quiz_data["title"],
            submitted=False,
            score=None,
            questions=quiz_data["questions"],
        )
        
        # The payload has answers nested: {"answers": {"q1": "value", ...}}
        answers = payload.get("answers", payload)
        
        # Grade the quiz
        graded_state = grade_quiz(current_state, answers)
        
        # Build updated widget
        updated_widget = build_quiz_widget(graded_state)
        
        # Replace the widget with the graded version
        yield ThreadItemReplacedEvent(
            item=sender.model_copy(update={"widget": updated_widget}),
        )
        
        # Send a congratulatory message
        correct = sum(1 for q in graded_state.questions if q["isCorrect"])
        total = len(graded_state.questions)
        
        if correct == total:
            message = f"🎉 Perfect score! You got all {total} questions correct!"
        elif correct >= total * 0.7:
            message = f"Great job! You scored {correct}/{total}. Keep it up!"
        elif correct >= total * 0.5:
            message = f"Not bad! You scored {correct}/{total}. Review the hints for the ones you missed."
        else:
            message = f"You scored {correct}/{total}. Check the hints and try again!"
        
        message_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[AssistantMessageContent(text=message)],
        )
        yield ThreadItemDoneEvent(item=message_item)

    async def _handle_quiz_reset(
        self,
        thread: ThreadMetadata,
        sender: WidgetItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle quiz reset - clear answers and allow retake."""
        
        if not sender:
            logger.warning("quiz.reset received without sender widget")
            return
        
        # Load quiz state from the quiz store
        quiz_data = self.quiz_store.load(thread.id)
        
        if not quiz_data:
            logger.error(f"Could not find quiz state for thread {thread.id}")
            return
        
        current_state = QuizState(
            title=quiz_data["title"],
            submitted=True,  # It was submitted, now we're resetting
            score=None,
            questions=quiz_data["questions"],
        )
        
        # Reset the quiz
        reset_state = reset_quiz(current_state)
        
        # Build updated widget
        updated_widget = build_quiz_widget(reset_state)
        
        # Replace the widget with the reset version
        yield ThreadItemReplacedEvent(
            item=sender.model_copy(update={"widget": updated_widget}),
        )
        
        message_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[AssistantMessageContent(text="Quiz reset! Give it another try. 💪")],
        )
        yield ThreadItemDoneEvent(item=message_item)

    def _extract_quiz_state(self, widget_item: WidgetItem) -> QuizState | None:
        """Extract QuizState from a widget item."""
        try:
            # The widget contains the rendered template, but we stored the data
            # We need to get it from the widget's data attribute
            widget = widget_item.widget
            
            logger.info(f"[_extract_quiz_state] Widget type: {type(widget)}")
            logger.info(f"[_extract_quiz_state] Widget attrs: {dir(widget)}")
            
            # WidgetRoot has a 'data' attribute with the template variables
            if hasattr(widget, "data"):
                data = widget.data
                logger.info(f"[_extract_quiz_state] Got data from .data attr: {type(data)}")
            elif hasattr(widget, "model_dump"):
                dumped = widget.model_dump()
                logger.info(f"[_extract_quiz_state] Dumped widget: {dumped}")
                data = dumped.get("data", dumped)
            elif isinstance(widget, dict):
                data = widget.get("data", widget)
            else:
                logger.error(f"Unknown widget format: {type(widget)}")
                return None
            
            logger.info(f"[_extract_quiz_state] Extracted data: {data}")
            logger.info(f"[_extract_quiz_state] Questions: {data.get('questions', [])}")
            
            return QuizState(
                title=data.get("title", "Quiz"),
                submitted=data.get("submitted", False),
                score=data.get("score"),
                questions=data.get("questions", []),
            )
        except Exception as e:
            logger.exception(f"Error extracting quiz state: {e}")
            return None


def create_quiz_server() -> QuizServer:
    """Create and return a configured quiz server."""
    return QuizServer()

