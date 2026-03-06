"""
services/whatsapp.py — Sends messages back to WhatsApp via the Meta Graph API.
"""

import logging
import httpx
from memocore.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

async def send_whatsapp_message(to: str, text: str) -> None:
    """
    Sends a text message to a user via the WhatsApp Cloud API.
    """
    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Successfully sent WhatsApp message to %s.", to)
    except httpx.HTTPStatusError as exc:
        logger.error(
            "WhatsApp API returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text,
        )
    except Exception as exc:
        logger.exception("Failed to send WhatsApp message to %s", to)
