import json
import logging
from datetime import date

from groq import Groq

from memocore.config import get_settings
from memocore.schemas.intent import ParsedIntent

logger = logging.getLogger(__name__)
settings = get_settings()


class IntentParserError(Exception):
    """Raised when the AI response cannot be parsed into a valid intent."""


_SYSTEM_PROMPT_TEMPLATE = """
You are MemoCore, an intent extraction engine for a WhatsApp productivity assistant.

Your only job is to convert the user's message into strict JSON.

You are NOT a chatbot.
You do NOT explain.
You do NOT refuse.
You do NOT add any text outside JSON.

Today's date is {today} ({weekday}).

Allowed intents:
- add_task
- complete_task
- delete_task
- delete_all_tasks
- add_event
- add_recurring_event
- query_schedule
- query_tasks
- update_event
- delete_event
- unknown

Always return this JSON shape:

{{
  "intent": "string",
  "confidence": 0.0,
  "payload": {{}}
}}

Rules:
- confidence must be between 0 and 1
- payload must always be an object
- if unclear, return:
  {{
    "intent": "unknown",
    "confidence": 0.3,
    "payload": {{}}
  }}
- interpret casual language naturally
- infer likely meaning when the user is informal
- if the user says they finished something, prefer complete_task
- if the user says remove/delete a task, prefer delete_task
- if the user says remove/delete all tasks, prefer delete_all_tasks
- if the user asks what tasks they have, prefer query_tasks
- if the user asks what they have scheduled, prefer query_schedule

DATE RULES — critical:
- Always resolve relative dates ("tomorrow", "next Monday", "in 3 days") to ISO 8601 format: YYYY-MM-DD
- Always resolve times to HH:MM (24-hour) format
- For query_schedule, resolve "today", "this week", "tomorrow" into start_date and end_date (ISO 8601)
- Never return natural language for date or time fields

Examples:

User: buy milk tomorrow
Output:
{{
  "intent": "add_task",
  "confidence": 0.95,
  "payload": {{
    "title": "buy milk",
    "due_date": "2026-03-10"
  }}
}}

User: I finished the math homework
Output:
{{
  "intent": "complete_task",
  "confidence": 0.96,
  "payload": {{
    "title": "math homework"
  }}
}}

User: done with groceries
Output:
{{
  "intent": "complete_task",
  "confidence": 0.90,
  "payload": {{
    "title": "groceries"
  }}
}}

User: delete task buy milk
Output:
{{
  "intent": "delete_task",
  "confidence": 0.96,
  "payload": {{
    "title": "buy milk"
  }}
}}

User: delete all tasks
Output:
{{
  "intent": "delete_all_tasks",
  "confidence": 0.99,
  "payload": {{}}
}}

User: what tasks do i have
Output:
{{
  "intent": "query_tasks",
  "confidence": 0.98,
  "payload": {{}}
}}

User: meeting tomorrow at 5pm
Output:
{{
  "intent": "add_event",
  "confidence": 0.96,
  "payload": {{
    "title": "meeting",
    "date": "2026-03-10",
    "time": "17:00"
  }}
}}

User: math class every monday at 6pm
Output:
{{
  "intent": "add_recurring_event",
  "confidence": 0.97,
  "payload": {{
    "title": "math class",
    "recurrence_pattern": "every monday",
    "time": "18:00"
  }}
}}

User: what do i have today
Output:
{{
  "intent": "query_schedule",
  "confidence": 0.98,
  "payload": {{
    "start_date": "2026-03-09",
    "end_date": "2026-03-09"
  }}
}}

User: what do i have this week
Output:
{{
  "intent": "query_schedule",
  "confidence": 0.97,
  "payload": {{
    "start_date": "2026-03-09",
    "end_date": "2026-03-15"
  }}
}}
"""


def _build_system_prompt() -> str:
    today = date.today()
    return _SYSTEM_PROMPT_TEMPLATE.format(
        today=today.isoformat(),
        weekday=today.strftime("%A"),
    )


class AgentParser:
    """Handles communication with Groq."""

    def __init__(self) -> None:
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def parse(self, message: str) -> ParsedIntent:
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": _build_system_prompt()},
                    {"role": "user", "content": message},
                ],
                temperature=0,
                max_completion_tokens=300,
            )
        except Exception as exc:
            logger.exception("Groq API request failed")
            raise IntentParserError(f"Groq API error: {exc}") from exc

        raw_output = (completion.choices[0].message.content or "").strip()
        logger.info("Groq response: %s", raw_output)

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
            return ParsedIntent(**data, raw_text=message)
        except Exception as exc:
            logger.error("Intent schema mismatch: %s", data)
            raise IntentParserError("Parsed intent schema mismatch") from exc


agent_parser = AgentParser()
