"""
schemas/task.py — Pydantic request/response schemas for Tasks.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

PriorityLiteral = Literal["low", "medium", "high"]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: PriorityLiteral = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[PriorityLiteral] = None
    is_completed: Optional[bool] = None


class TaskRead(BaseModel):
    id: str
    title: str
    description: Optional[str]
    due_date: Optional[date]
    priority: str
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
