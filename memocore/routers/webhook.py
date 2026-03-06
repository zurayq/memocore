"""
routers/webhook.py — FastAPI router for the incoming message webhook.

Architecture decision: The webhook endpoint is kept deliberately thin.
It performs three jobs only:
  1. Authorise the sender (phone number check).
  2. Delegate parsing to the AI agent.
  3. Delegate action to the agent router.
All business logic lives in services/; this layer only orchestrates.

WhatsApp Cloud API sends a GET request to verify the webhook and POST
requests for incoming messages.
"""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from memocore.agent import agent_parser, IntentParserError
from memocore.agent_router import dispatch
from memocore.config import get_settings
from memocore.database import get_db
from memocore.schemas.webhook import WebhookPayload

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["Webhook"])


# ------------------------------------------------------------------ #
# WhatsApp webhook verification endpoint (required by Meta)
# ------------------------------------------------------------------ #
@router.get(
    "",
    summary="Verify webhook",
    description="Meta webhook verification endpoint used when registering the webhook."
)
async def verify_webhook(request: Request):
    """
    Meta sends a GET request to verify the webhook with:
      hub.mode
      hub.verify_token
      hub.challenge

    We must return the challenge value if the token matches.
    """

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return PlainTextResponse(content=challenge)

    logger.warning("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


# ------------------------------------------------------------------ #
# Incoming message handler
# ------------------------------------------------------------------ #
@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Receive incoming message",
    description=(
        "Simulated WhatsApp webhook. Authorises sender, parses intent via DeepSeek (OpenRouter), "
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
        return {"status": "ignored", "reason": "unauthorised sender"}

    logger.info("Processing message from authorised user: %s", payload.from_number)

    # ------------------------------------------------------------------ #
    # Step 2 — Parse intent with AI
    # ------------------------------------------------------------------ #
    try:
        intent = await asyncio.to_thread(agent_parser.parse, payload.body)
    except IntentParserError as exc:
        logger.error("Intent parsing failed: %s", exc)
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


# ------------------------------------------------------------------ #
# Health endpoint
# ------------------------------------------------------------------ #
@router.get("/health", tags=["Health"], summary="Health check")
async def health() -> dict:
    """Simple liveness probe — returns 200 if the application is running."""
    return {"status": "ok", "service": settings.APP_NAME}
