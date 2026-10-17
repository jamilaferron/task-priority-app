"""Which routines and events happen on a day, and what still needs ticking.

Plain rules, no AI:
- A routine happens on a day if it is active, the weekday matches, and none of
  its break calendars has a break covering that day.
- Tomorrow's checklist appears from 18:00.
- The week-ahead check (school and work items only) appears on Sunday for the
  coming week, and again on Monday if it wasn't finished.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ChecklistTick, OneOffEvent, Routine
from .schedule_schemas import ChecklistItemOut, DayEntryOut, DayOut, ScheduleOut, WeekCheckOut, WeekItemOut

TOMORROW_FROM = time(18, 0)
WEEK_CHECK_CATEGORIES = {"school", "work"}
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass
class Occurrence:
    source: str  # "routine:3" or "event:7"
    title: str
    person: str
    category: str
    time: str | None
    items: list[str]


def item_key(name: str) -> str:
    return name.strip().lower()


def is_paused(routine: Routine, day: date) -> bool:
    return any(p.start_date <= day <= p.end_date for cal in routine.paused_by for p in cal.periods)


def occurrences_on(db: Session, day: date) -> list[Occurrence]:
    """Everything happening on a day, sorted by time (untimed first)."""
    found: list[Occurrence] = []
    for r in db.scalars(select(Routine).where(Routine.active.is_(True))):
        if day.weekday() in r.weekdays and not is_paused(r, day):
            found.append(Occurrence(f"routine:{r.id}", r.title, r.person, r.category, r.time, list(r.items)))
    for e in db.scalars(select(OneOffEvent).where(OneOffEvent.on_date == day)):
        found.append(Occurrence(f"event:{e.id}", e.title, e.person, "event", e.time, list(e.items)))
    found.sort(key=lambda o: (o.time or "", o.title.lower()))
    return found


def ticked_keys(db: Session, scope: str, period: date) -> set[tuple[str, str]]:
    rows = db.scalars(select(ChecklistTick).where(ChecklistTick.scope == scope, ChecklistTick.period == period))
    return {(t.source, t.item) for t in rows}


def build_day(db: Session, day: date) -> DayOut:
    ticked = ticked_keys(db, "day", day)
    entries = [
        DayEntryOut(
            source=o.source,
            title=o.title,
            person=o.person,
            time=o.time,
            items=[ChecklistItemOut(name=i, ticked=(o.source, item_key(i)) in ticked) for i in o.items],
        )
        for o in occurrences_on(db, day)
    ]
    complete = all(item.ticked for entry in entries for item in entry.items)
    return DayOut(day=day, entries=entries, complete=complete)


def build_week_check(db: Session, week_start: date) -> WeekCheckOut | None:
    """Every school and work item needed Monday to Sunday, merged by name."""
    ticked = ticked_keys(db, "week", week_start)
    needed: dict[str, WeekItemOut] = {}
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        for o in occurrences_on(db, day):
            if o.category not in WEEK_CHECK_CATEGORIES:
                continue
            for name in o.items:
                key = item_key(name)
                if key not in needed:
                    needed[key] = WeekItemOut(name=name, ticked=("week", key) in ticked, needed_for=[])
                needed[key].needed_for.append(f"{DAY_NAMES[day.weekday()]} {o.title}")
    if not needed:
        return None
    items = list(needed.values())
    return WeekCheckOut(week_start=week_start, items=items, complete=all(i.ticked for i in items))


def week_check_start(today: date) -> date | None:
    """Sunday -> tomorrow's Monday. Monday -> today. Other days -> no week check."""
    if today.weekday() == 6:
        return today + timedelta(days=1)
    if today.weekday() == 0:
        return today
    return None


def build_schedule(db: Session, now_local: datetime) -> ScheduleOut:
    """Everything the screen needs, for a given local date and time."""
    today = now_local.date()
    tomorrow = build_day(db, today + timedelta(days=1)) if now_local.time() >= TOMORROW_FROM else None
    start = week_check_start(today)
    return ScheduleOut(
        today=build_day(db, today),
        tomorrow=tomorrow,
        week_check=build_week_check(db, start) if start else None,
    )


def set_tick(db: Session, scope: str, period: date, source: str, item: str, ticked: bool) -> None:
    key = item_key(item)
    existing = db.scalar(
        select(ChecklistTick).where(
            ChecklistTick.scope == scope,
            ChecklistTick.period == period,
            ChecklistTick.source == source,
            ChecklistTick.item == key,
        )
    )
    if ticked and existing is None:
        db.add(ChecklistTick(scope=scope, period=period, source=source, item=key))
    elif not ticked and existing is not None:
        db.delete(existing)
    db.commit()
