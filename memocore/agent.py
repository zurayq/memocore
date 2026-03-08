    import json
    import logging

    from groq import Groq

    from memocore.config import get_settings
    from memocore.schemas.intent import ParsedIntent

    logger = logging.getLogger(__name__)
    settings = get_settings()


    class IntentParserError(Exception):
    """Raised when the AI response cannot be parsed into a valid intent."""


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
    """


    class AgentParser:
    """Handles communication with Groq."""

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def parse(self, message: str) -> ParsedIntent:
        try:
            completion = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
            )

            raw_output = completion.choices[0].message.content

            start = raw_output.find("{")
            end = raw_output.rfind("}") + 1

            if start == -1 or end == -1:
                raise IntentParserError("No JSON returned from model")

            data = json.loads(raw_output[start:end])

            return ParsedIntent(**data, raw_text=message)

        except Exception as exc:
            logger.exception("Intent parsing failed")
            raise IntentParserError(str(exc))


    agent_parser = AgentParser()
