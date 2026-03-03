"""
schemas/event.py — Pydantic request/response schemas for Events.
"""

from datetime import date, datetime, time
from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    date: date
    time: time | None = None
    location: str | None = Field(default=None, max_length=500)


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    date: date | None = None
    time: time | None = None
    location: str | None = None


class EventRead(BaseModel):
    id: str
    title: str
    description: str | None
    date: date
    time: time | None
    location: str | None
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
