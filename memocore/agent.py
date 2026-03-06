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

Respond ONLY with JSON.

{
  "intent": "<intent>",
  "confidence": 0.0,
  "payload": {}
}
"""


class IntentParserError(Exception):
    pass


class AgentParser:

    def __init__(self):

        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is missing")

        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": "https://memocore.onrender.com",
                "X-Title": "MemoCore"
            }
        )

    def parse(self, user_message: str) -> ParsedIntent:

        logger.info("Sending message to DeepSeek via OpenRouter")

        try:
            response = self._client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0
            )

        except Exception as exc:
            logger.exception("OpenRouter API call failed")
            raise IntentParserError(f"OpenRouter API error: {exc}") from exc

        raw_content = response.choices[0].message.content or ""

        logger.info("DeepSeek raw response: %s", raw_content)

        # Extract JSON safely
        start = raw_content.find("{")
        end = raw_content.rfind("}") + 1

        if start == -1 or end == 0:
            raise IntentParserError(f"No JSON returned: {raw_content}")

        json_str = raw_content[start:end]

        try:
            data = json.loads(json_str)

        except json.JSONDecodeError as exc:
            raise IntentParserError(
                f"Invalid JSON returned: {json_str}"
            ) from exc

        try:
            intent = ParsedIntent(**data, raw_text=user_message)

        except Exception as exc:
            raise IntentParserError(
                f"Schema mismatch: {exc}"
            ) from exc

        logger.info(
            "Parsed intent=%s confidence=%.2f",
            intent.intent,
            intent.confidence
        )

        return intent


agent_parser = AgentParser()
