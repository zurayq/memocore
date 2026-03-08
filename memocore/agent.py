"""
agent.py — AI Intent Parser using Groq

This module converts natural language messages into structured intents
for MemoCore using Groq's OpenAI-compatible API.
"""

import json
import logging
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
You are MemoCore, a productivity assistant.

Your job is to convert a user's message into structured JSON.

Supported intents:

add_task
add_event
add_recurring_event
query_schedule
update_event
delete_event
unknown

You MUST return ONLY valid JSON.

Never explain anything.
Never include text outside JSON.

JSON format:

{
"intent": "add_task",
"confidence": 0.95,
"payload": {
"title": "Buy groceries"
}
}

If the message is unclear:

{
"intent": "unknown",
"confidence": 0.5,
"payload": {}
}
"""

class AgentParser:
"""Handles communication with Groq."""

```
def __init__(self) -> None:
    self.client = Groq(api_key=settings.GROQ_API_KEY)

def parse(self, message: str) -> ParsedIntent:
    """
    Send user message to Groq and return ParsedIntent.
    """

    try:
        completion = self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            temperature=0.2,
            max_completion_tokens=512,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
        )

    except Exception as exc:
        logger.exception("Groq API request failed")
        raise IntentParserError(f"Groq API error: {exc}") from exc

    raw_output = completion.choices[0].message.content.strip()

    logger.info("Groq response: %s", raw_output)

    # ------------------------------------------------------------
    # Extract JSON safely
    # ------------------------------------------------------------

    start = raw_output.find("{")
    end = raw_output.rfind("}") + 1

    if start == -1 or end == 0:
        raise IntentParserError("No JSON returned from model")

    json_str = raw_output[start:end]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON returned: %s", json_str)
        raise IntentParserError("Invalid JSON returned by model") from exc

    try:
        intent = ParsedIntent(**data, raw_text=message)
    except Exception as exc:
        logger.error("Intent schema mismatch: %s", data)
        raise IntentParserError("Parsed intent schema mismatch") from exc

    return intent
```

# Singleton instance

agent_parser = AgentParser()
