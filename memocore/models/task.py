"""
models/task.py — SQLAlchemy ORM model for to-do / action items.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from memocore.database import Base


class Task(Base):
    """Represents an action item / to-do with an optional due date."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional due date — tasks without a due date are valid (open-ended)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Priority string: "low" | "medium" | "high"
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium"
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

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
        return f"<Task id={self.id!r} title={self.title!r} completed={self.is_completed}>"
