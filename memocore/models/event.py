"""
models/event.py — SQLAlchemy ORM model for one-time calendar events.
"""

import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from memocore.database import Base


class Event(Base):
    """Represents a single (non-recurring) calendar event."""

    __tablename__ = "events"

    # UUID primary key — avoids sequential ID enumeration and works across
    # distributed systems without coordination.
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stored as separate Date and Time columns so we can efficiently query
    # "all events on DATE X" without parsing datetime strings.
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time: Mapped[time | None] = mapped_column(Time, nullable=True)

    location: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Flag set once a reminder has been sent to avoid duplicate alerts
    reminder_sent: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Event id={self.id!r} title={self.title!r} date={self.date}>"
