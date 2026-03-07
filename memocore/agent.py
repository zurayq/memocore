"""
agent.py — AI Intent Parser using DeepSeek directly.

This module converts natural language messages into structured intents
for MemoCore. It uses DeepSeek's chat model via the OpenAI-compatible API.
"""

import json
import logging
import os

from groq import Groq

from memocore.config import get_settings
from memocore.schemas.intent import ParsedIntent

logger = logging.getLogger(__name__)
settings = get_settings()


class IntentParserError(Exception):
    """Raised when the AI response cannot be parsed into a valid intent."""


# ------------------------------------------------------------
# System prompt
# ------------------------------------------------------------

SYSTEM_PROMPT = """
You are MemoCore, a personal productivity assistant.

Your job is to convert a user's message into JSON describing their intent.

Supported intents:

add_task
add_event
add_recurring_event
query_schedule
update_event
delete_event
unknown

Return ONLY valid JSON.

Example:

{
  "intent": "add_task",
  "confidence": 0.92,
  "payload": {
    "title": "Buy groceries"
  }
}
"""


class AgentParser:
    """Handles communication with the DeepSeek API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def parse(self, message: str) -> ParsedIntent:
        """
        Send user message to DeepSeek and return ParsedIntent.
        """

        try:
            completion = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You extract task or event intents from user messages."},
                    {"role": "user", "content": message},
                ],
            )
        except Exception as exc:
            logger.exception("Groq API request failed")
            raise IntentParserError(f"Groq API error: {exc}") from exc

        raw_output = completion.choices[0].message.content

        logger.info("Groq response: %s", raw_output)

        # ------------------------------------------------------------
        # Extract JSON safely
        # ------------------------------------------------------------

        start = raw_output.find("{")
        end = raw_output.rfind("}") + 1

        if start == -1 or end == -1:
            raise IntentParserError("No JSON returned from model")

        json_str = raw_output[start:end]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise IntentParserError("Invalid JSON returned by model") from exc

        try:
            intent = ParsedIntent(**data, raw_text=message)
        except Exception as exc:
            raise IntentParserError("Parsed intent schema mismatch") from exc

        return intent


agent_parser = AgentParser()
