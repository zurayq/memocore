"""
routers/webhook.py — FastAPI router for the incoming message webhook.

Architecture decision: The webhook endpoint is kept deliberately thin.
It performs three jobs only:
  1. Authorise the sender (phone number check).
  2. Delegate parsing to the AI agent.
  3. Delegate action to the agent router.
All business logic lives in services/; this layer only orchestrates.

WhatsApp Cloud API sends a POST to this endpoint. For simulation we accept
a flat JSON body matching our WebhookPayload schema.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from memocore.agent import agent_parser, IntentParserError
from memocore.agent_router import dispatch
from memocore.config import get_settings
from memocore.database import get_db
from memocore.schemas.webhook import WebhookPayload

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Receive incoming message",
    description=(
        "Simulated WhatsApp webhook. Authorises sender, parses intent via OpenAI, "
        "routes to the correct handler, and returns a response string."
    ),
)
async def receive_message(
    payload: WebhookPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Main webhook handler.

    Always returns HTTP 200 — WhatsApp requires a 200 within 15 seconds or
    it will retry the delivery. We fail silently for unauthorised senders to
    avoid leaking information about who is / isn't registered.
    """
    # ------------------------------------------------------------------ #
    # Step 1 — Authorise sender
    # ------------------------------------------------------------------ #
    if payload.from_number != settings.ALLOWED_USER_PHONE:
        logger.warning(
            "Ignoring message from unauthorised sender: %s", payload.from_number
        )
        # Return 200 immediately; do not process or log the message body
        return {"status": "ignored", "reason": "unauthorised sender"}

    logger.info("Processing message from authorised user: %s", payload.from_number)

    # ------------------------------------------------------------------ #
    # Step 2 — Parse intent with AI
    # ------------------------------------------------------------------ #
    try:
        intent = await agent_parser.parse(payload.body)
    except IntentParserError as exc:
        logger.error("Intent parsing failed: %s", exc)
        # Do not expose internal errors to the caller; return a graceful reply
        return {
            "status": "error",
            "reply": "Sorry, I had trouble understanding that. Please try again.",
        }

    # ------------------------------------------------------------------ #
    # Step 3 — Route intent to handler
    # ------------------------------------------------------------------ #
    reply = await dispatch(intent, db)

    logger.info("Reply: %s", reply)
    return {"status": "processed", "intent": intent.intent, "reply": reply}


@router.get("/health", tags=["Health"], summary="Health check")
async def health() -> dict:
    """Simple liveness probe — returns 200 if the application is running."""
    return {"status": "ok", "service": settings.APP_NAME}
