import logging
from datetime import date, time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from memocore.schemas.intent import ParsedIntent
from memocore.schemas.event import EventCreate, EventUpdate
from memocore.schemas.task import TaskCreate, TaskUpdate
from memocore.schemas.recurring_event import RecurringEventCreate
from memocore.services import event_service, task_service, recurring_event_service

logger = logging.getLogger(__name__)


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


async def handle_add_recurring_event(payload: dict[str, Any], db: AsyncSession) -> str:
    title = payload.get("title", "Untitled recurring event")
    pattern = payload.get("recurrence_pattern")
    if not pattern:
        return "❌ Please specify a recurrence pattern."

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


async def handle_complete_task(payload: dict[str, Any], db: AsyncSession) -> str:
    title = payload.get("title")
    if not title:
        return "❌ Please tell me which task you completed."
    task = await task_service.update_task_by_title(
        db,
        title,
        TaskUpdate(is_completed=True),
    )
    if task is None:
        return f"❌ I couldn't find a task called **{title}**."
    return f"✅ Marked **{task.title}** as completed."


async def handle_delete_task(payload: dict[str, Any], db: AsyncSession) -> str:
    title = payload.get("title")
    if not title:
        return "❌ Please tell me which task to delete."
    deleted = await task_service.delete_task_by_title(db, title)
    if not deleted:
        return f"❌ I couldn't find a task called **{title}**."
    return f"🗑️ Deleted task **{title}**."


async def handle_delete_all_tasks(payload: dict[str, Any], db: AsyncSession) -> str:
    count = await task_service.delete_all_tasks(db)
    return f"🗑️ Deleted {count} task(s)."


async def handle_query_tasks(payload: dict[str, Any], db: AsyncSession) -> str:
    tasks = await task_service.get_tasks(db, include_completed=False)
    if not tasks:
        return "✅ You have no open tasks."

    lines = ["📝 Open tasks:"]
    for t in tasks:
        due = f" (due {t.due_date})" if t.due_date else ""
        lines.append(f"  • [{t.priority}] {t.title}{due}")
    return "\n".join(lines)


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
        "  - Add task: buy groceries\n"
        "  - Delete all tasks\n"
        "  - I finished the math homework\n"
        "  - What tasks do I have?"
    )


_HANDLERS = {
    "add_event": handle_add_event,
    "add_recurring_event": handle_add_recurring_event,
    "add_task": handle_add_task,
    "complete_task": handle_complete_task,
    "delete_task": handle_delete_task,
    "delete_all_tasks": handle_delete_all_tasks,
    "query_schedule": handle_query_schedule,
    "query_tasks": handle_query_tasks,
    "update_event": handle_update_event,
    "delete_event": handle_delete_event,
    "unknown": handle_unknown,
}


async def dispatch(intent: ParsedIntent, db: AsyncSession) -> str:
    handler = _HANDLERS.get(intent.intent, handle_unknown)
    logger.info("Dispatching intent=%s to handler=%s", intent.intent, handler.__name__)
    try:
        return await handler(intent.payload, db)
    except Exception as exc:
        logger.exception("Handler %s raised an unexpected error", handler.__name__)
        return f"❌ An internal error occurred: {exc}"
