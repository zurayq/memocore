"""
models/recurring_event.py — SQLAlchemy ORM model for recurring calendar events.

Architecture decision: We store recurring events as a separate table rather
than a flag on Event. This cleanly separates the scheduling logic; when the
scheduler fires it reads RecurringEvent rows and generates virtual occurrences
without polluting the main events table.
"""

import uuid
from datetime import datetime, time

from sqlalchemy import DateTime, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from memocore.database import Base


class RecurringEvent(Base):
    """
    Recurring event template. The recurrence_pattern field uses a human-
    readable string like "daily", "weekly:monday", "monthly:15", etc.
    In a production system you might switch to RFC 5545 RRULE strings.
    """

    __tablename__ = "recurring_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Recurrence string — e.g. "daily", "weekly:monday,wednesday", "monthly:1"
    recurrence_pattern: Mapped[str] = mapped_column(String(255), nullable=False)

    # Time of day the recurring event occurs (optional)
    time: Mapped[time | None] = mapped_column(Time, nullable=True)

    location: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Active flag — soft-delete by setting is_active=False
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<RecurringEvent id={self.id!r} title={self.title!r} "
            f"pattern={self.recurrence_pattern!r}>"
        )
