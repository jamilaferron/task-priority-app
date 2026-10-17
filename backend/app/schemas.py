"""Shapes of API requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .models import Task
from .ranking import latest_start
from .timeutils import from_storage


class TaskIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class ClarifyIn(BaseModel):
    answer: str = Field(min_length=1, max_length=1000)


class SiriReply(BaseModel):
    """What the Shortcut reads. `message` is always safe for Siri to speak."""

    status: Literal["added", "needs_info"]
    task_id: int
    message: str
    question: str | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    raw_input: str
    deadline: datetime | None
    estimated_minutes: int | None
    consequence: int | None
    status: str
    pending_question: str | None
    created_at: datetime
    completed_at: datetime | None
    latest_start: datetime | None

    @classmethod
    def from_task(cls, task: Task) -> "TaskOut":
        return cls(
            id=task.id,
            title=task.title,
            raw_input=task.raw_input,
            deadline=from_storage(task.deadline),
            estimated_minutes=task.estimated_minutes,
            consequence=task.consequence,
            status=task.status,
            pending_question=task.pending_question,
            created_at=from_storage(task.created_at),
            completed_at=from_storage(task.completed_at),
            latest_start=from_storage(latest_start(task)),
        )


class BoardOut(BaseModel):
    overdue: list[TaskOut]
    ranked: list[TaskOut]
    whenever: list[TaskOut]
    needs_info: list[TaskOut]
    generated_at: datetime


class TaskPatch(BaseModel):
    """Every field optional. Sending "deadline": null moves a task to the whenever pile."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    deadline: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=10080)
    consequence: int | None = Field(default=None, ge=1, le=5)
