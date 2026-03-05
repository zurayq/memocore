"""
schemas/event.py — Pydantic request/response schemas for Events.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    date: date
    time: Optional[time] = None
    location: Optional[str] = Field(default=None, max_length=500)


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    date: Optional[date] = None
    time: Optional[time] = None
    location: Optional[str] = None


class EventRead(BaseModel):
    id: str
    title: str
    description: Optional[str]
    date: date
    time: Optional[time]
    location: Optional[str]
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
