"""Helpers that convert ChatKit thread items into model-friendly inputs."""

from __future__ import annotations

import logging
from typing import Any

from chatkit.agents import ThreadItemConverter
from chatkit.types import FileAttachment, HiddenContextItem, ImageAttachment
from openai.types.responses import ResponseInputTextParam
from openai.types.responses.response_input_item_param import Message

from .file_store import file_store

logger = logging.getLogger(__name__)


class BasicThreadItemConverter(ThreadItemConverter):
    """Adds HiddenContextItem and Attachment support."""

    async def hidden_context_to_input(self, item: HiddenContextItem):
        return Message(
            type="message",
            content=[
                ResponseInputTextParam(
                    type="input_text",
                    text=item.content,
                )
            ],
            role="user",
        )

    async def attachment_to_message_content(
        self, 
        attachment: FileAttachment | ImageAttachment,
    ) -> dict[str, Any] | None:
        """Convert an attachment to message content for the model."""
        logger.info(f"[attachment_to_message_content] Processing: {attachment.name}, type: {attachment.mime_type}")
        
        # Try to get the file data from our store
        stored_file = file_store.load(attachment.id)
        
        if stored_file and stored_file.data:
            # For PDFs - include the content as base64 for the model
            if attachment.mime_type == "application/pdf":
                import base64
                b64_data = base64.b64encode(stored_file.data).decode("utf-8")
                
                # GPT-4o can handle files via the file input type
                return {
                    "type": "input_file",
                    "file_data": f"data:{attachment.mime_type};base64,{b64_data}",
                    "filename": attachment.name,
                }
        
        # Fallback: just describe the attachment
        return {
            "type": "input_text",
            "text": f"[User attached a file: {attachment.name} ({attachment.mime_type}). Please create a quiz based on this document.]",
        }

