"""Endpoints for routines, one-off events, break calendars and checklists."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import require_api_key
from .database import Base, get_db
from .models import BreakCalendar, BreakPeriod, OneOffEvent, Routine
from .schedule import build_schedule, set_tick
from .schedule_schemas import (
    CalendarIn,
    CalendarOut,
    EventIn,
    EventOut,
    PeriodIn,
    PeriodOut,
    RoutineIn,
    RoutineOut,
    ScheduleOut,
    TickIn,
)
from .timeutils import to_local, utcnow

router = APIRouter(dependencies=[Depends(require_api_key)])


def get_or_404(db: Session, model: type[Base], obj_id: int):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return obj


def local_now():
    return to_local(utcnow())


# --- Schedule and checklists (used by the wall screen) ----------------------


@router.get("/schedule", response_model=ScheduleOut, tags=["schedule"])
def get_schedule(db: Session = Depends(get_db)):
    """Today's agenda and checklist, tomorrow's from 18:00, and the week check on Sunday/Monday."""
    return build_schedule(db, local_now())


@router.post("/checklist/tick", response_model=ScheduleOut, tags=["schedule"])
def tick_item(body: TickIn, db: Session = Depends(get_db)):
    """Tick or untick one item. Returns the updated schedule."""
    set_tick(db, body.scope, body.period, body.source, body.item, body.ticked)
    return build_schedule(db, local_now())


# --- Routines ---------------------------------------------------------------


def routine_out(r: Routine) -> RoutineOut:
    return RoutineOut(
        id=r.id,
        title=r.title,
        person=r.person,
        category=r.category,
        weekdays=r.weekdays,
        time=r.time,
        items=r.items,
        active=r.active,
        paused_by=[c.id for c in r.paused_by],
    )


def load_calendars(db: Session, ids: list[int]) -> list[BreakCalendar]:
    if not ids:
        return []
    calendars = list(db.scalars(select(BreakCalendar).where(BreakCalendar.id.in_(ids))))
    if len(calendars) != len(set(ids)):
        raise HTTPException(422, "Unknown break calendar")
    return calendars


@router.get("/routines", response_model=list[RoutineOut], tags=["routines"])
def list_routines(db: Session = Depends(get_db)):
    return [routine_out(r) for r in db.scalars(select(Routine).order_by(Routine.title))]


@router.post("/routines", response_model=RoutineOut, status_code=201, tags=["routines"])
def create_routine(body: RoutineIn, db: Session = Depends(get_db)):
    routine = Routine(**body.model_dump(exclude={"paused_by"}))
    routine.paused_by = load_calendars(db, body.paused_by)
    db.add(routine)
    db.commit()
    return routine_out(routine)


@router.put("/routines/{routine_id}", response_model=RoutineOut, tags=["routines"])
def update_routine(routine_id: int, body: RoutineIn, db: Session = Depends(get_db)):
    routine = get_or_404(db, Routine, routine_id)
    for field, value in body.model_dump(exclude={"paused_by"}).items():
        setattr(routine, field, value)
    routine.paused_by = load_calendars(db, body.paused_by)
    db.commit()
    return routine_out(routine)


@router.delete("/routines/{routine_id}", status_code=204, tags=["routines"])
def delete_routine(routine_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Routine, routine_id))
    db.commit()


# --- One-off events ---------------------------------------------------------


def event_out(e: OneOffEvent) -> EventOut:
    return EventOut(id=e.id, title=e.title, person=e.person, on_date=e.on_date, time=e.time, items=e.items)


@router.get("/events", response_model=list[EventOut], tags=["events"])
def list_events(from_date: date | None = None, db: Session = Depends(get_db)):
    """Upcoming events (from today unless from_date is given), soonest first."""
    start = from_date or local_now().date()
    rows = db.scalars(
        select(OneOffEvent).where(OneOffEvent.on_date >= start).order_by(OneOffEvent.on_date, OneOffEvent.time)
    )
    return [event_out(e) for e in rows]


@router.post("/events", response_model=EventOut, status_code=201, tags=["events"])
def create_event(body: EventIn, db: Session = Depends(get_db)):
    event = OneOffEvent(**body.model_dump())
    db.add(event)
    db.commit()
    return event_out(event)


@router.put("/events/{event_id}", response_model=EventOut, tags=["events"])
def update_event(event_id: int, body: EventIn, db: Session = Depends(get_db)):
    event = get_or_404(db, OneOffEvent, event_id)
    for field, value in body.model_dump().items():
        setattr(event, field, value)
    db.commit()
    return event_out(event)


@router.delete("/events/{event_id}", status_code=204, tags=["events"])
def delete_event(event_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, OneOffEvent, event_id))
    db.commit()


# --- Break calendars --------------------------------------------------------


def calendar_out(c: BreakCalendar) -> CalendarOut:
    return CalendarOut(
        id=c.id,
        name=c.name,
        periods=[
            PeriodOut(id=p.id, name=p.name, start_date=p.start_date, end_date=p.end_date) for p in c.periods
        ],
    )


@router.get("/calendars", response_model=list[CalendarOut], tags=["breaks"])
def list_calendars(db: Session = Depends(get_db)):
    return [calendar_out(c) for c in db.scalars(select(BreakCalendar).order_by(BreakCalendar.name))]


@router.post("/calendars", response_model=CalendarOut, status_code=201, tags=["breaks"])
def create_calendar(body: CalendarIn, db: Session = Depends(get_db)):
    calendar = BreakCalendar(name=body.name.strip())
    db.add(calendar)
    db.commit()
    return calendar_out(calendar)


@router.put("/calendars/{calendar_id}", response_model=CalendarOut, tags=["breaks"])
def rename_calendar(calendar_id: int, body: CalendarIn, db: Session = Depends(get_db)):
    calendar = get_or_404(db, BreakCalendar, calendar_id)
    calendar.name = body.name.strip()
    db.commit()
    return calendar_out(calendar)


@router.delete("/calendars/{calendar_id}", status_code=204, tags=["breaks"])
def delete_calendar(calendar_id: int, db: Session = Depends(get_db)):
    """Deletes the calendar and its breaks. Routines it paused simply stop being paused by it."""
    db.delete(get_or_404(db, BreakCalendar, calendar_id))
    db.commit()


@router.post("/calendars/{calendar_id}/periods", response_model=CalendarOut, status_code=201, tags=["breaks"])
def add_period(calendar_id: int, body: PeriodIn, db: Session = Depends(get_db)):
    calendar = get_or_404(db, BreakCalendar, calendar_id)
    calendar.periods.append(BreakPeriod(name=body.name.strip(), start_date=body.start_date, end_date=body.end_date))
    db.commit()
    db.refresh(calendar)  # re-sort periods by date
    return calendar_out(calendar)


@router.delete("/periods/{period_id}", status_code=204, tags=["breaks"])
def delete_period(period_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, BreakPeriod, period_id))
    db.commit()
