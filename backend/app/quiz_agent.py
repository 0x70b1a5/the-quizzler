"""Quiz agent that creates multiple-choice quizzes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any

from agents import Agent, ModelSettings, RunContextWrapper, StopAtTools, function_tool
from chatkit.agents import AgentContext
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ThreadItemDoneEvent,
)
from pydantic import BaseModel, ConfigDict, Field

from .memory_store import MemoryStore
from .quiz_store import QuizStore
from .widgets.quiz_widget import QuizState, build_quiz_widget

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuizOption(BaseModel):
    """A single answer option for a quiz question."""
    label: str = Field(description="The display text for this option")
    value: str = Field(description="The value/key for this option")


class QuizQuestion(BaseModel):
    """A single quiz question with multiple choice options."""
    id: str = Field(description="Unique identifier like q1, q2, q3")
    prompt: str = Field(description="The question text")
    options: list[QuizOption] = Field(description="The answer options")
    correctValue: str = Field(description="The value of the correct option")
    hint: str = Field(description="Hint shown when the answer is wrong")
    explanation: str = Field(description="Explanation shown when the answer is correct, explaining why it's right")


class QuizAgentContext(AgentContext):
    """Context passed to the quiz agent during execution."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    store: Annotated[MemoryStore, Field(exclude=True)]
    quiz_store: Annotated[QuizStore, Field(exclude=True)]
    request_context: dict[str, Any]


@function_tool(
    description_override=(
        "Display a quiz widget to the user with multiple choice questions.\n"
        "- `title`: The title of the quiz\n"
        "- `questions`: List of QuizQuestion objects"
    )
)
async def show_quiz(
    ctx: RunContextWrapper[QuizAgentContext],
    title: str,
    questions: list[QuizQuestion],
):
    """
    Display a quiz widget to the user.
    
    Args:
        title: The title of the quiz
        questions: List of QuizQuestion objects
    """
    logger.info(f"[TOOL CALL] show_quiz: {title} with {len(questions)} questions")
    
    # Build the questions data
    questions_data = [
        {
            "id": q.id,
            "prompt": q.prompt,
            "options": [
                {"label": o.label, "value": o.value, "disabled": False}
                for o in q.options
            ],
            "correctValue": q.correctValue,
            "hint": q.hint,
            "explanation": q.explanation,
            "userAnswer": "",
            "isCorrect": False,
        }
        for q in questions
    ]
    
    quiz_state = QuizState(
        title=title,
        submitted=False,
        score=None,
        questions=questions_data,
    )
    
    # Save the quiz state for later grading (keyed by thread ID)
    thread_id = ctx.context.thread.id
    ctx.context.quiz_store.save(thread_id, {
        "title": title,
        "questions": questions_data,
    })
    logger.info(f"[show_quiz] Saved quiz state for thread {thread_id}")
    
    widget = build_quiz_widget(quiz_state)
    
    # Stream the widget to the client
    await ctx.context.stream_widget(widget, copy_text=f"Quiz: {title}")
    
    # Send a follow-up message
    await ctx.context.stream(
        ThreadItemDoneEvent(
            item=AssistantMessageItem(
                thread_id=ctx.context.thread.id,
                id=ctx.context.generate_id("message"),
                created_at=datetime.now(),
                content=[
                    AssistantMessageContent(
                        text=f"Here's your quiz on {title}! Answer all the questions and click 'Submit answers' when you're ready."
                    )
                ],
            ),
        )
    )


quiz_agent = Agent[QuizAgentContext](
    name="The Quizzler",
    model="gpt-4o",
    instructions="""You are The Quizzler, a quiz master who creates multiple-choice quizzes.

## ABSOLUTE RULES - NEVER BREAK THESE:
1. NEVER output JSON in your response
2. NEVER show quiz questions as text
3. NEVER explain what you're about to do - just DO IT
4. ALWAYS use the show_quiz tool - this is the ONLY way to display quizzes

## When a user asks for a quiz or uploads a document:
1. Silently analyze the content
2. Create 3-5 multiple choice questions  
3. Call show_quiz IMMEDIATELY with NO preamble

## Question format:
- id: "q1", "q2", "q3", etc.
- prompt: The question text  
- options: Array of {label: "Answer text", value: "answer_key"} (4 options each)
- correctValue: Must exactly match one option's value
- hint: Helpful hint shown when wrong
- explanation: Educational commentary shown when correct, explaining WHY

DO NOT write any text before calling show_quiz. Just call the tool.""",
    tools=[show_quiz],
    tool_use_behavior=StopAtTools(stop_at_tool_names=[show_quiz.name]),
    model_settings=ModelSettings(tool_choice="required"),
)
