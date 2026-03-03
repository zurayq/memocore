"""
services/event_service.py — Business logic for one-time calendar events.

Architecture decision: Services are pure async functions that accept an
AsyncSession as their first argument (dependency-injected by the router).
This makes them independently testable without spinning up FastAPI.
"""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memocore.models.event import Event
from memocore.schemas.event import EventCreate, EventUpdate

logger = logging.getLogger(__name__)


async def create_event(db: AsyncSession, data: EventCreate) -> Event:
    """Persist a new calendar event and return the ORM instance."""
    event = Event(
        title=data.title,
        description=data.description,
        date=data.date,
        time=data.time,
        location=data.location,
    )
    db.add(event)
    await db.flush()  # flush to get the auto-generated id without committing
    await db.refresh(event)
    logger.info("Created event id=%s title=%r", event.id, event.title)
    return event


async def get_events(
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Event]:
    """
    Return events in [start_date, end_date] (inclusive).
    If no dates are provided, return all upcoming events (today onwards).
    """
    stmt = select(Event)
    if start_date:
        stmt = stmt.where(Event.date >= start_date)
    if end_date:
        stmt = stmt.where(Event.date <= end_date)
    stmt = stmt.order_by(Event.date, Event.time)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_event(
    db: AsyncSession, event_id: str, data: EventUpdate
) -> Event | None:
    """Apply partial updates to an existing event. Returns None if not found."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        logger.warning("update_event: event %s not found", event_id)
        return None

    # Only update fields that were explicitly provided (exclude_unset)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    await db.flush()
    await db.refresh(event)
    logger.info("Updated event id=%s", event.id)
    return event


async def delete_event(db: AsyncSession, event_id: str) -> bool:
    """Hard-delete an event. Returns True if the event existed."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        logger.warning("delete_event: event %s not found", event_id)
        return False

    await db.delete(event)
    logger.info("Deleted event id=%s", event_id)
    return True


async def get_events_due_soon(
    db: AsyncSession, target_date: date, target_time_window_minutes: int = 15
) -> list[Event]:
    """
    Return unreminded events whose date == target_date.
    Used by the scheduler to identify events needing a reminder.
    Filtering by exact time is handled in the caller to keep this query simple.
    """
    stmt = (
        select(Event)
        .where(Event.date == target_date)
        .where(Event.reminder_sent.is_(False))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def mark_reminder_sent(db: AsyncSession, event_id: str) -> None:
    """Mark an event's reminder_sent flag so duplicates are avoided."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event:
        event.reminder_sent = True
        await db.flush()
