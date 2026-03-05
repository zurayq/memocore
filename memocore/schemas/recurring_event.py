"""
schemas/recurring_event.py — Pydantic schemas for RecurringEvents.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, Field


class RecurringEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    recurrence_pattern: str = Field(
        ...,
        description='e.g. "daily", "weekly:monday", "monthly:15"',
        max_length=255,
    )
    time: Optional[time] = None
    location: Optional[str] = Field(default=None, max_length=500)


class RecurringEventRead(BaseModel):
    id: str
    title: str
    description: Optional[str]
    recurrence_pattern: str
    time: Optional[time]
    location: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
