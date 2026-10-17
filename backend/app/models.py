"""The tasks table."""

from datetime import datetime

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .timeutils import utcnow


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_input: Mapped[str] = mapped_column(Text)  # exactly what was said to Siri
    title: Mapped[str] = mapped_column(String(200), default="")
    deadline: Mapped[datetime | None] = mapped_column(default=None)  # naive UTC; None = whenever pile
    estimated_minutes: Mapped[int | None] = mapped_column(default=None)
    consequence: Mapped[int | None] = mapped_column(default=None)  # 1-5
    status: Mapped[str] = mapped_column(String(20), default="needs_info")  # needs_info / active / done
    pending_question: Mapped[str | None] = mapped_column(Text, default=None)
    # Follow-up history: [{"question": "...", "answer": "..."}]. Reassign, don't mutate in place.
    clarifications: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
