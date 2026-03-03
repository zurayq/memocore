"""
schemas/task.py — Pydantic request/response schemas for Tasks.
"""

from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field

PriorityLiteral = Literal["low", "medium", "high"]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    due_date: date | None = None
    priority: PriorityLiteral = "medium"


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    due_date: date | None = None
    priority: PriorityLiteral | None = None
    is_completed: bool | None = None


class TaskRead(BaseModel):
    id: str
    title: str
    description: str | None
    due_date: date | None
    priority: str
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
