"""
agent.py — AI Intent Parser using DeepSeek via OpenRouter.

Architecture decision: The agent is intentionally kept stateless. It receives
a message string, calls the OpenRouter API, and returns a ParsedIntent object.
This makes it trivially testable: mock the client and assert on the returned
Pydantic model. All routing decisions are made by the caller (agent_router).

The system prompt is deliberately specific and asks for JSON-only output.
DeepSeek follows this instruction reliably at temperature=0.
"""

import json
import logging

from openai import OpenAI

from memocore.config import get_settings
from memocore.schemas.intent import ParsedIntent

logger = logging.getLogger(__name__)
settings = get_settings()

# ------------------------------------------------------------------ #
# System prompt — defines the AI's persona and JSON contract
# ------------------------------------------------------------------ #
SYSTEM_PROMPT = """
You are MemoCore, a personal AI assistant that manages a user's calendar and tasks.

Your ONLY job is to convert the user's natural-language message into a JSON object.

Supported intents:
- add_event           → add a one-time calendar event
- add_recurring_event → add a repeating event (daily / weekly / monthly)
- add_task            → add an action item / to-do
- query_schedule      → list upcoming events or tasks
- update_event        → modify an existing event
- delete_event        → remove an existing event
- unknown             → you cannot confidently classify the message

Output format — respond with ONLY a JSON object, no prose:
{
  "intent": "<one of the intent labels above>",
  "confidence": <float 0.0–1.0>,
  "payload": {
    // for add_event / update_event:
    "title": "<string>",
    "date": "<YYYY-MM-DD>",
    "time": "<HH:MM>",          // 24h, optional
    "description": "<string>",  // optional
    "location": "<string>",     // optional
    "event_id": "<uuid>",       // required only for update/delete

    // for add_recurring_event:
    "recurrence_pattern": "<daily|weekly:<day>|monthly:<day-of-month>>",

    // for add_task:
    "title": "<string>",
    "due_date": "<YYYY-MM-DD>", // optional
    "priority": "<low|medium|high>",

    // for query_schedule:
    "start_date": "<YYYY-MM-DD>",  // optional filter
    "end_date": "<YYYY-MM-DD>"     // optional filter
  }
}

Rules:
- Dates must be ISO 8601 (YYYY-MM-DD). Resolve relative dates like "tomorrow"
  against today's date (provided in the user message context).
- If a required field is missing and cannot be inferred, set confidence ≤ 0.5.
- Never include explanatory text — output the JSON object only.
"""


class IntentParserError(Exception):
    """Raised when the model returns a non-parseable or invalid response."""


class AgentParser:
    """
    Wraps the OpenRouter client and exposes a single `parse` method.

    Dependency injection pattern: the client is created once and reused across
    requests. In tests, pass a mock client to the constructor.
    """

    def __init__(self) -> None:
        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )

    def parse(self, user_message: str) -> ParsedIntent:
        """
        Send a user message to DeepSeek via OpenRouter and return a validated ParsedIntent.

        Raises:
            IntentParserError: if the model returns invalid JSON or a JSON
                               structure that doesn't conform to ParsedIntent.
        """
        logger.info("Sending message to DeepSeek (OpenRouter) for intent parsing")

        try:
            response = self._client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0,
            )
        except Exception as exc:
            logger.exception("OpenRouter API call failed")
            raise IntentParserError(f"OpenRouter API error: {exc}") from exc

        raw_content = response.choices[0].message.content or ""
        logger.debug("Raw DeepSeek response: %s", raw_content)

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise IntentParserError(
                f"OpenAI returned non-JSON content: {raw_content!r}"
            ) from exc

        try:
            intent = ParsedIntent(**data, raw_text=user_message)
        except Exception as exc:
            raise IntentParserError(
                f"OpenAI response did not match ParsedIntent schema: {exc}"
            ) from exc

        logger.info(
            "Parsed intent=%s confidence=%.2f", intent.intent, intent.confidence
        )
        return intent


# Module-level singleton — instantiated once at import time so the OpenRouter
# client (which maintains a connection pool) is reused across requests.
agent_parser = AgentParser()
