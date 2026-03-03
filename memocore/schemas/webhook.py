"""
schemas/webhook.py — Pydantic models for the incoming webhook payload.

We deliberately keep this loose (extra="allow") so that real WhatsApp Cloud
API payloads (which have many extra fields) don't cause validation errors.
The fields we actually need are explicitly declared.
"""

from pydantic import BaseModel, Field


class WebhookPayload(BaseModel):
    """
    Simulated WhatsApp-style incoming message payload.

    In production this would mirror the WhatsApp Cloud API object structure.
    For simulation, a simple flat payload is used.
    """

    from_number: str = Field(
        ...,
        alias="from",
        description="Sender's phone number in E.164 format, e.g. +1234567890",
    )
    body: str = Field(..., description="Text body of the message")
    message_id: str | None = Field(
        default=None, description="Optional message ID for idempotency"
    )

    model_config = {"extra": "allow", "populate_by_name": True}
