"""Database tables: tasks, plus routines, one-off events, break calendars and checklist ticks."""

from datetime import date, datetime

from sqlalchemy import JSON, Column, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


# ---------------------------------------------------------------------------
# Phase 2: routines and checklists
# ---------------------------------------------------------------------------

# Many-to-many link: which break calendars pause which routines.
routine_pauses = Table(
    "routine_pauses",
    Base.metadata,
    Column("routine_id", ForeignKey("routines.id"), primary_key=True),
    Column("calendar_id", ForeignKey("break_calendars.id"), primary_key=True),
)


class BreakCalendar(Base):
    """A named set of date ranges, e.g. 'School holidays' or 'Performing arts breaks'."""

    __tablename__ = "break_calendars"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    periods: Mapped[list["BreakPeriod"]] = relationship(
        back_populates="calendar", cascade="all, delete-orphan", order_by="BreakPeriod.start_date"
    )
    routines: Mapped[list["Routine"]] = relationship(secondary=routine_pauses, back_populates="paused_by")


class BreakPeriod(Base):
    """One break, e.g. October half term. Both dates are included."""

    __tablename__ = "break_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    calendar_id: Mapped[int] = mapped_column(ForeignKey("break_calendars.id"))
    name: Mapped[str] = mapped_column(String(80), default="")
    start_date: Mapped[date]
    end_date: Mapped[date]
    calendar: Mapped[BreakCalendar] = relationship(back_populates="periods")


class Routine(Base):
    """Something that happens every week on the same day(s), with an optional checklist."""

    __tablename__ = "routines"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    person: Mapped[str] = mapped_column(String(60), default="")  # e.g. "Kenzo", "Me"
    category: Mapped[str] = mapped_column(String(20), default="other")  # school / work / activity / other
    weekdays: Mapped[list] = mapped_column(JSON, default=list)  # 0 = Monday ... 6 = Sunday
    time: Mapped[str | None] = mapped_column(String(5), default=None)  # "HH:MM", or None for no set time
    items: Mapped[list] = mapped_column(JSON, default=list)  # checklist, e.g. ["P.E. kit"]
    active: Mapped[bool] = mapped_column(default=True)
    paused_by: Mapped[list[BreakCalendar]] = relationship(secondary=routine_pauses, back_populates="routines")


class OneOffEvent(Base):
    """A single dated event, e.g. a dentist appointment."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    person: Mapped[str] = mapped_column(String(60), default="")
    on_date: Mapped[date]
    time: Mapped[str | None] = mapped_column(String(5), default=None)
    items: Mapped[list] = mapped_column(JSON, default=list)


class ChecklistTick(Base):
    """One ticked item.

    scope "day":  period = the day, source = "routine:3" or "event:7"
    scope "week": period = the Monday of that week, source = "week"
    item is stored lower-case so "P.E. kit" and "p.e. kit" count as the same thing.
    """

    __tablename__ = "checklist_ticks"
    __table_args__ = (UniqueConstraint("scope", "period", "source", "item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(10))
    period: Mapped[date]
    source: Mapped[str] = mapped_column(String(40))
    item: Mapped[str] = mapped_column(String(200))
    ticked_at: Mapped[datetime] = mapped_column(default=utcnow)
