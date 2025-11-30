"""
Quiz widget builder - creates the Quiz Taker widget with proper state.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from chatkit.widgets import WidgetRoot, WidgetTemplate

# Load the widget template using absolute path
_widget_dir = os.path.dirname(os.path.abspath(__file__))
_widget_path = os.path.join(_widget_dir, "quiz_taker.widget")
quiz_widget_template = WidgetTemplate.from_file(_widget_path)


@dataclass
class QuizState:
    """State for the quiz widget."""
    title: str
    submitted: bool
    score: str | None
    questions: list[dict[str, Any]] = field(default_factory=list)


def build_quiz_widget(state: QuizState) -> WidgetRoot:
    """Build a quiz widget from the given state."""
    return quiz_widget_template.build(
        data={
            "title": state.title,
            "submitted": state.submitted,
            "score": state.score or "",
            "questions": state.questions,
        }
    )


import logging

logger = logging.getLogger(__name__)


def grade_quiz(state: QuizState, answers: dict[str, str]) -> QuizState:
    """
    Grade the quiz and return updated state.
    
    Args:
        state: Current quiz state
        answers: Dict mapping question IDs to user answers (e.g. {"q1": "paris", "q2": "4"})
    
    Returns:
        Updated QuizState with grading results
    """
    logger.info(f"[grade_quiz] Answers received: {answers}")
    logger.info(f"[grade_quiz] Questions in state: {len(state.questions)}")
    
    correct_count = 0
    total_count = len(state.questions)
    
    graded_questions = []
    for q in state.questions:
        qid = q["id"]
        correct_value = q["correctValue"]
        
        # Try different answer key formats
        user_answer = answers.get(qid, answers.get(f"answers.{qid}", ""))
        is_correct = user_answer == correct_value
        
        logger.info(f"[grade_quiz] Q {qid}: user='{user_answer}' correct='{correct_value}' match={is_correct}")
        
        if is_correct:
            correct_count += 1
        
        graded_questions.append({
            **q,
            "userAnswer": user_answer,
            "isCorrect": is_correct,
            # Disable options after submission
            "options": [
                {**opt, "disabled": True} for opt in q["options"]
            ],
        })
    
    return QuizState(
        title=state.title,
        submitted=True,
        score=f"{correct_count}/{total_count}",
        questions=graded_questions,
    )


def reset_quiz(state: QuizState) -> QuizState:
    """Reset the quiz to its initial unsubmitted state."""
    reset_questions = []
    for q in state.questions:
        reset_questions.append({
            **q,
            "userAnswer": "",
            "isCorrect": False,
            "options": [
                {**opt, "disabled": False} for opt in q["options"]
            ],
        })
    
    return QuizState(
        title=state.title,
        submitted=False,
        score=None,
        questions=reset_questions,
    )

