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

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from memocore.agent import agent_parser, IntentParserError
from memocore.agent_router import dispatch
from memocore.config import get_settings
from memocore.database import get_db
from memocore.services.whatsapp import send_whatsapp_message

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
        logger.info("Webhook verified successfully.")
        return PlainTextResponse(content=challenge)

    logger.warning("Webhook verification failed.")
    raise HTTPException(status_code=403, detail="Verification failed")


# ------------------------------------------------------------------ #
# Incoming message handler
# ------------------------------------------------------------------ #
@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Receive incoming message",
    description=(
        "WhatsApp Cloud API webhook. Authorises sender, parses intent via DeepSeek (OpenRouter), "
        "routes to the correct handler, and sends a response via the WhatsApp Graph API."
    ),
)
async def receive_message(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Main webhook handler.

    Always returns HTTP 200 — WhatsApp requires a 200 within 15 seconds or
    it will retry the delivery. We fail silently for unauthorised senders to
    avoid leaking information about who is / isn't registered.
    """
    try:
        payload = await request.json()
    except Exception:
        return Response(status_code=200)

    # ------------------------------------------------------------------ #
    # Parse WhatsApp structure
    # ------------------------------------------------------------------ #
    try:
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        
        # Check if it's a message event
        if "messages" not in value or not value["messages"]:
            return Response(status_code=200)
            
        message = value["messages"][0]
        
        # Only process text messages
        if message.get("type") != "text":
            return Response(status_code=200)
            
        from_number = message["from"]
        if not from_number.startswith("+"):
            from_number = f"+{from_number}"
            
        body = message["text"]["body"]
        
    except (IndexError, KeyError, TypeError):
        # Ignore malformed or unsupported event types gracefully
        return Response(status_code=200)

    # ------------------------------------------------------------------ #
    # Step 1 — Authorise sender
    # ------------------------------------------------------------------ #
    if from_number != settings.ALLOWED_USER_PHONE:
        logger.warning(
            "Ignoring message from unauthorised sender: %s", from_number
        )
        # Return 200 immediately; do not process or log the message body
        return Response(status_code=200)

    logger.info("Processing message from authorised user: %s", from_number)

    # ------------------------------------------------------------------ #
    # Step 2 — Parse intent with AI
    # ------------------------------------------------------------------ #
    try:
        intent = await asyncio.to_thread(agent_parser.parse, body)
    except IntentParserError as exc:
        logger.error("Intent parsing failed: %s", exc)
        await send_whatsapp_message(
            to=from_number,
            text=f"Parser error: {exc}"
        )
        return Response(status_code=200)

    # ------------------------------------------------------------------ #
    # Step 3 — Route intent to handler
    # ------------------------------------------------------------------ #
    reply = await dispatch(intent, db)

    logger.info("Reply: %s", reply)
    
    # ------------------------------------------------------------------ #
    # Step 4 — Send reply back to user
    # ------------------------------------------------------------------ #
    await send_whatsapp_message(to=from_number, text=reply)
    
    return Response(status_code=200)


# ------------------------------------------------------------------ #
# Health endpoint
# ------------------------------------------------------------------ #
@router.get("/health", tags=["Health"], summary="Health check")
async def health() -> dict:
    """Simple liveness probe — returns 200 if the application is running."""
    return {"status": "ok", "service": settings.APP_NAME}
