"""
agent_router.py — Maps parsed intents to their service-layer handlers.

Architecture decision: The router lives outside the `routers/` HTTP layer so
that the same dispatch table can be called from unit tests, CLI tools, or
alternative transports (Telegram, email, etc.) without touching FastAPI.

Each handler receives:
  - payload: dict  (extracted parameters from the AI)
  - db: AsyncSession

And returns a human-readable string reply that is sent back to the user.
"""

import logging
from datetime import date, time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from memocore.schemas.intent import ParsedIntent
from memocore.schemas.event import EventCreate, EventUpdate
from memocore.schemas.task import TaskCreate
from memocore.schemas.recurring_event import RecurringEventCreate
from memocore.services import event_service, task_service, recurring_event_service

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Helper utilities
# ------------------------------------------------------------------ #

def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        logger.warning("Could not parse date %r", value)
        return None


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        logger.warning("Could not parse time %r", value)
        return None


# ------------------------------------------------------------------ #
# Intent handlers
# ------------------------------------------------------------------ #

async def handle_add_event(payload: dict[str, Any], db: AsyncSession) -> str:
    title = payload.get("title", "Untitled event")
    event_date = _parse_date(payload.get("date"))
    if not event_date:
        return "❌ I need a date to create an event. Please provide one (e.g. 2025-06-15)."

    data = EventCreate(
        title=title,
        description=payload.get("description"),
        date=event_date,
        time=_parse_time(payload.get("time")),
        location=payload.get("location"),
    )
    event = await event_service.create_event(db, data)
    time_str = f" at {event.time}" if event.time else ""
    return f"✅ Event **{event.title}** added on {event.date}{time_str}."


async def handle_add_recurring_event(
    payload: dict[str, Any], db: AsyncSession
) -> str:
    title = payload.get("title", "Untitled recurring event")
    pattern = payload.get("recurrence_pattern")
    if not pattern:
        return "❌ Please specify a recurrence pattern (e.g. daily, weekly:monday)."

    data = RecurringEventCreate(
        title=title,
        description=payload.get("description"),
        recurrence_pattern=pattern,
        time=_parse_time(payload.get("time")),
        location=payload.get("location"),
    )
    event = await recurring_event_service.create_recurring_event(db, data)
    return f"🔁 Recurring event **{event.title}** added (pattern: {event.recurrence_pattern})."


async def handle_add_task(payload: dict[str, Any], db: AsyncSession) -> str:
    title = payload.get("title", "Untitled task")
    priority = payload.get("priority", "medium")
    if priority not in ("low", "medium", "high"):
        priority = "medium"

    data = TaskCreate(
        title=title,
        description=payload.get("description"),
        due_date=_parse_date(payload.get("due_date")),
        priority=priority,
    )
    task = await task_service.create_task(db, data)
    due_str = f" (due {task.due_date})" if task.due_date else ""
    return f"📝 Task **{task.title}**{due_str} added with {task.priority} priority."


async def handle_query_schedule(payload: dict[str, Any], db: AsyncSession) -> str:
    start = _parse_date(payload.get("start_date")) or date.today()
    end = _parse_date(payload.get("end_date"))

    events = await event_service.get_events(db, start_date=start, end_date=end)
    tasks = await task_service.get_tasks(db, include_completed=False)

    lines: list[str] = [f"📅 Schedule from {start}:"]
    if events:
        lines.append("\n*Events:*")
        for e in events:
            t = f" {e.time}" if e.time else ""
            lines.append(f"  • {e.date}{t} — {e.title}")
    else:
        lines.append("  No events found.")

    lines.append("\n*Open Tasks:*")
    if tasks:
        for t in tasks:
            due = f" (due {t.due_date})" if t.due_date else ""
            lines.append(f"  • [{t.priority}] {t.title}{due}")
    else:
        lines.append("  No open tasks.")

    return "\n".join(lines)


async def handle_update_event(payload: dict[str, Any], db: AsyncSession) -> str:
    event_id = payload.get("event_id")
    if not event_id:
        return "❌ Please provide the event ID you want to update."

    data = EventUpdate(
        title=payload.get("title"),
        description=payload.get("description"),
        date=_parse_date(payload.get("date")),
        time=_parse_time(payload.get("time")),
        location=payload.get("location"),
    )
    event = await event_service.update_event(db, event_id, data)
    if event is None:
        return f"❌ Event with ID {event_id} not found."
    return f"✏️ Event **{event.title}** updated."


async def handle_delete_event(payload: dict[str, Any], db: AsyncSession) -> str:
    event_id = payload.get("event_id")
    if not event_id:
        return "❌ Please provide the event ID to delete."

    deleted = await event_service.delete_event(db, event_id)
    if not deleted:
        return f"❌ Event with ID {event_id} not found."
    return f"🗑️ Event {event_id} deleted."


async def handle_unknown(payload: dict[str, Any], db: AsyncSession) -> str:
    return (
        "I did not understand that. Try:\n"
        "  - Add a meeting tomorrow at 3pm\n"
        "  - Remind me every Monday at 9am\n"
        "  - Add task: buy groceries\n"
        "  - What is on my schedule this week?"
    )


# ------------------------------------------------------------------ #
# Dispatch table — easy to extend without touching conditionals
# ------------------------------------------------------------------ #
_HANDLERS = {
    "add_event": handle_add_event,
    "add_recurring_event": handle_add_recurring_event,
    "add_task": handle_add_task,
    "query_schedule": handle_query_schedule,
    "update_event": handle_update_event,
    "delete_event": handle_delete_event,
    "unknown": handle_unknown,
}


async def dispatch(intent: ParsedIntent, db: AsyncSession) -> str:
    """
    Route a ParsedIntent to the correct handler and return the reply string.

    If the intent label is unrecognised (shouldn't happen given the Pydantic
    validator, but defence in depth) we fall through to handle_unknown.
    """
    handler = _HANDLERS.get(intent.intent, handle_unknown)
    logger.info("Dispatching intent=%s to handler=%s", intent.intent, handler.__name__)
    try:
        return await handler(intent.payload, db)
    except Exception as exc:
        logger.exception("Handler %s raised an unexpected error", handler.__name__)
        return f"❌ An internal error occurred: {exc}"
