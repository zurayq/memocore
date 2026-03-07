"""
agent.py — AI Intent Parser using DeepSeek via OpenRouter.
"""

import json
import logging

from openai import OpenAI

from memocore.config import get_settings
from memocore.schemas.intent import ParsedIntent

logger = logging.getLogger(__name__)
settings = get_settings()

# ------------------------------------------------------------------ #
# System prompt
# ------------------------------------------------------------------ #
SYSTEM_PROMPT = """
You are MemoCore, a personal AI assistant that manages a user's calendar and tasks.

Your ONLY job is to convert the user's natural-language message into a JSON object.

Supported intents:
- add_event
- add_recurring_event
- add_task
- query_schedule
- update_event
- delete_event
- unknown

Respond ONLY with valid JSON.
Do not include explanations, markdown, or extra text.

Example output:
{
  "intent": "add_task",
  "confidence": 0.95,
  "payload": {
    "title": "Buy groceries",
    "priority": "medium"
  }
}
"""


class IntentParserError(Exception):
    """Raised when the model returns a non-parseable or invalid response."""


class AgentParser:
    """
    Stateless parser that sends a message to OpenRouter and returns ParsedIntent.
    """

    def __init__(self) -> None:
        raw_key = settings.OPENROUTER_API_KEY

        # Sanitize key aggressively
        api_key = (raw_key or "").strip().strip('"').strip("'")

        # Helpful debug without leaking full secret
        logger.warning(
            "OpenRouter key loaded: prefix=%r length=%d",
            api_key[:10],
            len(api_key),
        )

        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is empty after stripping")

        if not api_key.startswith("sk-or-"):
            raise RuntimeError(
                f"OPENROUTER_API_KEY looks wrong. Expected prefix 'sk-or-', got {api_key[:10]!r}"
            )

        self._client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://memocore.onrender.com",
                "X-Title": "MemoCore",
            },
        )

    def parse(self, user_message: str) -> ParsedIntent:
        """
        Send a user message to DeepSeek via OpenRouter and return ParsedIntent.
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
        logger.info("DeepSeek raw response: %s", raw_content)

        # Extract JSON safely even if the model adds extra text
        start = raw_content.find("{")
        end = raw_content.rfind("}") + 1

        if start == -1 or end == 0:
            raise IntentParserError(f"No JSON found in response: {raw_content}")

        json_str = raw_content[start:end]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise IntentParserError(f"Failed to parse JSON: {json_str}") from exc

        try:
            intent = ParsedIntent(**data, raw_text=user_message)
        except Exception as exc:
            raise IntentParserError(
                f"Response did not match ParsedIntent schema: {exc}"
            ) from exc

        logger.info(
            "Parsed intent=%s confidence=%.2f",
            intent.intent,
            intent.confidence,
        )
        return intent


agent_parser = AgentParser()
