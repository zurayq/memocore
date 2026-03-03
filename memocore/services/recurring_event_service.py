"""
services/recurring_event_service.py — Business logic for recurring events.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memocore.models.recurring_event import RecurringEvent
from memocore.schemas.recurring_event import RecurringEventCreate

logger = logging.getLogger(__name__)


async def create_recurring_event(
    db: AsyncSession, data: RecurringEventCreate
) -> RecurringEvent:
    event = RecurringEvent(
        title=data.title,
        description=data.description,
        recurrence_pattern=data.recurrence_pattern,
        time=data.time,
        location=data.location,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    logger.info(
        "Created recurring event id=%s pattern=%r", event.id, event.recurrence_pattern
    )
    return event


async def get_active_recurring_events(db: AsyncSession) -> list[RecurringEvent]:
    stmt = select(RecurringEvent).where(RecurringEvent.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def deactivate_recurring_event(
    db: AsyncSession, event_id: str
) -> RecurringEvent | None:
    result = await db.execute(
        select(RecurringEvent).where(RecurringEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        return None
    event.is_active = False
    await db.flush()
    return event
