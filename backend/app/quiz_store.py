"""
Simple in-memory store for quiz state.
Maps widget IDs to quiz state so we can grade answers later.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class QuizStore:
    """Store quiz state by widget ID for later grading."""

    def __init__(self) -> None:
        self._quizzes: dict[str, dict[str, Any]] = {}

    def save(self, widget_id: str, quiz_data: dict[str, Any]) -> None:
        """Save quiz state for a widget."""
        logger.info(f"[QuizStore] Saving quiz for widget {widget_id}")
        self._quizzes[widget_id] = quiz_data

    def load(self, widget_id: str) -> dict[str, Any] | None:
        """Load quiz state for a widget."""
        data = self._quizzes.get(widget_id)
        logger.info(f"[QuizStore] Loading quiz for widget {widget_id}: {'found' if data else 'not found'}")
        return data

    def delete(self, widget_id: str) -> None:
        """Delete quiz state for a widget."""
        self._quizzes.pop(widget_id, None)

