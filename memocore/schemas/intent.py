"""
schemas/intent.py — Pydantic model for the structured intent returned by the AI model.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


IntentLiteral = Literal[
    "add_task",
    "complete_task",
    "delete_task",
    "delete_all_tasks",
    "add_event",
    "add_recurring_event",
    "query_schedule",
    "query_tasks",
    "update_event",
    "delete_event",
    "unknown",
]


class ParsedIntent(BaseModel):
    """
    Structured output from the AI intent parser.

    `intent`  — one of the supported operation labels
    `payload` — free-form dict that each handler function knows how to consume
    `confidence` — 0-1 score from the model
    """

    intent: IntentLiteral = Field(
        ..., description="The classified operation to perform"
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted parameters needed to fulfil the intent",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Model's self-reported confidence (0–1)",
    )
    raw_text: Optional[str] = Field(
        default=None,
        description="Original user message for logging/debugging",
    )
