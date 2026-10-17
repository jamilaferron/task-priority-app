"""Request and response shapes for routines, events, break calendars and checklists."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Category = Literal["school", "work", "activity", "other"]
TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"  # "HH:MM", 24-hour


def clean_items(items: list[str]) -> list[str]:
    """Trim items, drop blanks and remove duplicates (ignoring case), keeping order."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in items:
        item = raw.strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            cleaned.append(item)
    return cleaned


# --- Routines ---------------------------------------------------------------


class RoutineIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    person: str = Field(default="", max_length=60)
    category: Category = "other"
    weekdays: list[int] = Field(min_length=1)  # 0 = Monday ... 6 = Sunday
    time: str | None = Field(default=None, pattern=TIME_PATTERN)
    items: list[str] = []
    active: bool = True
    paused_by: list[int] = []  # break calendar ids

    @field_validator("weekdays")
    @classmethod
    def check_weekdays(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("weekdays must be between 0 (Monday) and 6 (Sunday)")
        return sorted(set(value))

    @field_validator("items")
    @classmethod
    def tidy_items(cls, value: list[str]) -> list[str]:
        return clean_items(value)


class RoutineOut(RoutineIn):
    id: int


# --- One-off events ---------------------------------------------------------


class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    person: str = Field(default="", max_length=60)
    on_date: date
    time: str | None = Field(default=None, pattern=TIME_PATTERN)
    items: list[str] = []

    @field_validator("items")
    @classmethod
    def tidy_items(cls, value: list[str]) -> list[str]:
        return clean_items(value)


class EventOut(EventIn):
    id: int


# --- Break calendars --------------------------------------------------------


class PeriodIn(BaseModel):
    name: str = Field(default="", max_length=80)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def check_order(self) -> "PeriodIn":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class PeriodOut(PeriodIn):
    id: int


class CalendarIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CalendarOut(BaseModel):
    id: int
    name: str
    periods: list[PeriodOut]


# --- What the screen shows --------------------------------------------------


class ChecklistItemOut(BaseModel):
    name: str
    ticked: bool


class DayEntryOut(BaseModel):
    source: str  # "routine:3" or "event:7"; sent back when ticking
    title: str
    person: str
    time: str | None
    items: list[ChecklistItemOut]


class DayOut(BaseModel):
    day: date
    entries: list[DayEntryOut]
    complete: bool  # every item ticked (True when there is nothing to tick)


class WeekItemOut(BaseModel):
    name: str
    ticked: bool
    needed_for: list[str]  # e.g. ["Tue P.E.", "Thu P.E."]


class WeekCheckOut(BaseModel):
    week_start: date  # the Monday
    items: list[WeekItemOut]
    complete: bool


class ScheduleOut(BaseModel):
    today: DayOut
    tomorrow: DayOut | None  # only from 18:00
    week_check: WeekCheckOut | None  # only on Sunday and Monday


class TickIn(BaseModel):
    scope: Literal["day", "week"]
    period: date  # the day, or the Monday for a week check
    source: str = Field(min_length=1, max_length=40)  # entry source, or "week"
    item: str = Field(min_length=1, max_length=200)
    ticked: bool
