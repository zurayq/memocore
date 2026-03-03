"""
schemas/intent.py — Pydantic model for the structured intent returned by OpenAI.

Architecture decision: Using a discriminated union (Literal type on 'intent')
gives us compile-time and runtime exhaustiveness checking. Adding a new intent
only requires adding a new Literal variant and handler — the validator catches
unknown intents automatically.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


# All recognised intent labels
IntentLiteral = Literal[
    "add_event",
    "add_recurring_event",
    "add_task",
    "query_schedule",
    "update_event",
    "delete_event",
    "unknown",
]


class ParsedIntent(BaseModel):
    """
    Structured output from the AI intent parser.

    `intent`  — one of the supported operation labels
    `payload` — free-form dict that each handler function knows how to consume
    `confidence` — 0-1 score from the model (informational, logged but not acted on)
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
    raw_text: str | None = Field(
        default=None, description="Original user message for logging/debugging"
    )
