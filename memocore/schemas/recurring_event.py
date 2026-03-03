"""
schemas/recurring_event.py — Pydantic schemas for RecurringEvents.
"""

from datetime import datetime, time
from pydantic import BaseModel, Field


class RecurringEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    recurrence_pattern: str = Field(
        ...,
        description='e.g. "daily", "weekly:monday", "monthly:15"',
        max_length=255,
    )
    time: time | None = None
    location: str | None = Field(default=None, max_length=500)


class RecurringEventRead(BaseModel):
    id: str
    title: str
    description: str | None
    recurrence_pattern: str
    time: time | None
    location: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
