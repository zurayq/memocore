"""
agent.py — AI Intent Parser using DeepSeek directly.

This module converts natural language messages into structured intents
for MemoCore. It uses DeepSeek's chat model via the OpenAI-compatible API.
"""

import json
import logging
import os

from openai import OpenAI

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
        api_key = os.getenv("DEEPSEEK_API_KEY")

        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not set")

        logger.info("DeepSeek API key loaded")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

    def parse(self, message: str) -> ParsedIntent:
        """
        Send user message to DeepSeek and return ParsedIntent.
        """

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                temperature=0,
            )
        except Exception as exc:
            logger.exception("DeepSeek API request failed")
            raise IntentParserError(f"DeepSeek API error: {exc}") from exc

        raw_output = response.choices[0].message.content

        logger.info("DeepSeek response: %s", raw_output)

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
