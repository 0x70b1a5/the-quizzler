"""
Simple in-memory file storage for attachments.
In production, use a proper storage service like S3.
"""

from __future__ import annotations

import base64
import logging
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StoredFile:
    """A stored file with its metadata."""
    id: str
    filename: str
    content_type: str
    data: bytes
    size: int


class FileStore:
    """Simple in-memory file store."""

    def __init__(self) -> None:
        self._files: dict[str, StoredFile] = {}

    def save(self, filename: str, content_type: str, data: bytes) -> str:
        """Save a file and return its ID."""
        file_id = str(uuid.uuid4())
        self._files[file_id] = StoredFile(
            id=file_id,
            filename=filename,
            content_type=content_type,
            data=data,
            size=len(data),
        )
        logger.info(f"[FileStore] Saved file {filename} ({len(data)} bytes) as {file_id}")
        return file_id

    def load(self, file_id: str) -> StoredFile | None:
        """Load a file by ID."""
        return self._files.get(file_id)

    def delete(self, file_id: str) -> None:
        """Delete a file by ID."""
        self._files.pop(file_id, None)

    def get_data_url(self, file_id: str) -> str | None:
        """Get a data URL for the file (for passing to the model)."""
        stored = self._files.get(file_id)
        if not stored:
            return None
        b64 = base64.b64encode(stored.data).decode("utf-8")
        return f"data:{stored.content_type};base64,{b64}"


# Global file store instance
file_store = FileStore()

