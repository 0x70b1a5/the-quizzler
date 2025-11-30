"""
AttachmentStore implementation for handling file uploads.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from chatkit.store import AttachmentStore
from chatkit.types import FileAttachment

from .file_store import file_store

if TYPE_CHECKING:
    from .memory_store import MemoryStore

logger = logging.getLogger(__name__)


class QuizAttachmentStore(AttachmentStore[dict[str, Any]]):
    """Attachment store for the quiz app."""
    
    def __init__(self, memory_store: "MemoryStore" = None):
        self.memory_store = memory_store

    async def create_attachment(
        self,
        input: Any,
        context: dict[str, Any],
    ) -> FileAttachment:
        """Create an attachment from uploaded file data."""
        # Extract fields from input (could be dict or object)
        if isinstance(input, dict):
            filename = input.get("name", input.get("filename", "unknown"))
            content_type = input.get("mime_type", input.get("content_type", "application/octet-stream"))
            data = input.get("data")
        else:
            filename = getattr(input, "name", getattr(input, "filename", "unknown"))
            content_type = getattr(input, "mime_type", getattr(input, "content_type", "application/octet-stream"))
            data = getattr(input, "data", None)
        
        logger.info(f"[AttachmentStore] Creating attachment: {filename}, type: {content_type}")
        
        # Generate an ID for this attachment
        attachment_id = str(uuid.uuid4())
        
        # Store the file data if provided
        if data:
            file_store.save(
                filename=filename,
                content_type=content_type,
                data=data if isinstance(data, bytes) else data.encode(),
            )
        
        # Return FileAttachment with upload_url for two-phase upload
        # The client will PUT the file data to this URL
        upload_url = f"http://127.0.0.1:8087/chatkit/uploads/{attachment_id}"
        
        attachment = FileAttachment(
            id=attachment_id,
            name=filename,
            mime_type=content_type,
            type="file",
            upload_url=upload_url,
        )
        
        # Also save to the memory store so load_attachment can find it
        if self.memory_store:
            await self.memory_store.save_attachment(attachment, context)
        
        return attachment

    async def delete_attachment(
        self,
        attachment_id: str,
        context: dict[str, Any],
    ) -> None:
        """Delete an attachment."""
        logger.info(f"[AttachmentStore] Deleting attachment: {attachment_id}")
        file_store.delete(attachment_id)

    def generate_attachment_id(
        self,
        mime_type: str,
        context: dict[str, Any],
    ) -> str:
        """Generate a unique attachment ID."""
        return str(uuid.uuid4())

