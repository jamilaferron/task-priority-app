from datetime import date, datetime

from app.database import SessionLocal
from app.schedule import build_day, build_schedule
from conftest import HEADERS

# October 2026: Sun 18, Mon 19, Tue 20.
SUN = date(2026, 10, 18)
TUE = date(2026, 10, 20)


def setup_week(client):
    """Kenzo's Tuesday, roughly as described, plus one work routine."""
    school = client.post("/calendars", json={"name": "School holidays"}, headers=HEADERS).json()
    arts = client.post("/calendars", json={"name": "Performing arts breaks"}, headers=HEADERS).json()

    def routine(**fields):
        r = client.post("/routines", json=fields, headers=HEADERS)
        assert r.status_code == 201, r.text
        return r.json()

    routine(title="Breakfast club", person="Kenzo", category="school", weekdays=[1], time="08:00",
            paused_by=[school["id"]])
    routine(title="P.E.", person="Kenzo", category="school", weekdays=[1, 3], items=["P.E. kit"],
            paused_by=[school["id"]])
    routine(title="Packed lunch", person="Kenzo", category="school", weekdays=[1],
            items=["Sandwich", "Fruit", "Drink", "Snack"], paused_by=[school["id"]])
    routine(title="Performing arts", person="Kenzo", category="activity", weekdays=[1], time="17:30",
            items=["Dance shoes"], paused_by=[arts["id"]])
    routine(title="Staff briefing", person="Me", category="work", weekdays=[1], time="08:30",
            items=["Lanyard"], paused_by=[school["id"]])
    return school, arts


def test_tuesday_agenda_in_time_order(client):
    setup_week(client)
    with SessionLocal() as db:
        day = build_day(db, TUE)
    assert [e.title for e in day.entries] == [
        "P.E.", "Packed lunch", "Breakfast club", "Staff briefing", "Performing arts",
    ]  # untimed first, then by time
    assert day.complete is False


def test_school_holidays_pause_school_and_work_but_not_activities(client):
    school, _ = setup_week(client)
    r = client.post(f"/calendars/{school['id']}/periods",
                    json={"name": "Half term", "start_date": "2026-10-19", "end_date": "2026-10-23"},
                    headers=HEADERS)
    assert r.status_code == 201
    with SessionLocal() as db:
        day = build_day(db, TUE)
    assert [e.title for e in day.entries] == ["Performing arts"]


def test_activity_paused_by_its_own_breaks(client):
    _, arts = setup_week(client)
    client.post(f"/calendars/{arts['id']}/periods",
                json={"start_date": "2026-10-20", "end_date": "2026-10-20"}, headers=HEADERS)
    with SessionLocal() as db:
        titles = [e.title for e in build_day(db, TUE).entries]
    assert "Performing arts" not in titles
    assert "P.E." in titles


def test_week_check_on_sunday_merges_school_and_work_items(client):
    setup_week(client)
    with SessionLocal() as db:
        schedule = build_schedule(db, datetime(2026, 10, 18, 10, 0))  # Sunday morning
    check = schedule.week_check
    assert check is not None and check.week_start == date(2026, 10, 19)
    names = [i.name for i in check.items]
    assert "Dance shoes" not in names  # activities aren't in the week check
    pe = next(i for i in check.items if i.name == "P.E. kit")
    assert pe.needed_for == ["Tue P.E.", "Thu P.E."]
    assert "Lanyard" in names


def test_week_check_only_on_sunday_and_monday(client):
    setup_week(client)
    with SessionLocal() as db:
        assert build_schedule(db, datetime(2026, 10, 19, 7, 0)).week_check is not None  # Monday
        assert build_schedule(db, datetime(2026, 10, 20, 7, 0)).week_check is None  # Tuesday


def test_tomorrow_appears_from_six_pm(client):
    setup_week(client)
    with SessionLocal() as db:
        assert build_schedule(db, datetime(2026, 10, 19, 17, 59)).tomorrow is None
        tomorrow = build_schedule(db, datetime(2026, 10, 19, 18, 0)).tomorrow
    assert tomorrow is not None and tomorrow.day == TUE


def test_ticking_completes_the_week_check(client):
    setup_week(client)
    with SessionLocal() as db:
        items = build_schedule(db, datetime(2026, 10, 18, 10, 0)).week_check.items
    for item in items:
        r = client.post("/checklist/tick", headers=HEADERS, json={
            "scope": "week", "period": "2026-10-19", "source": "week", "item": item.name, "ticked": True,
        })
        assert r.status_code == 200
    with SessionLocal() as db:
        assert build_schedule(db, datetime(2026, 10, 19, 7, 0)).week_check.complete is True


def test_day_ticks_and_untick(client):
    setup_week(client)
    with SessionLocal() as db:
        lunch = next(e for e in build_day(db, TUE).entries if e.title == "Packed lunch")
    tick = {"scope": "day", "period": "2026-10-20", "source": lunch.source, "item": "Fruit", "ticked": True}
    client.post("/checklist/tick", json=tick, headers=HEADERS)
    with SessionLocal() as db:
        lunch = next(e for e in build_day(db, TUE).entries if e.title == "Packed lunch")
    assert [i.ticked for i in lunch.items] == [False, True, False, False]

    client.post("/checklist/tick", json={**tick, "ticked": False}, headers=HEADERS)
    with SessionLocal() as db:
        lunch = next(e for e in build_day(db, TUE).entries if e.title == "Packed lunch")
    assert not any(i.ticked for i in lunch.items)


def test_one_off_event_shows_on_its_day(client):
    client.post("/events", json={"title": "Dentist", "person": "Kenzo", "on_date": "2026-10-20",
                                 "time": "15:00", "items": ["Appointment letter"]}, headers=HEADERS)
    with SessionLocal() as db:
        day = build_day(db, TUE)
    assert [e.title for e in day.entries] == ["Dentist"]


def test_validation(client):
    bad_day = client.post("/routines", json={"title": "X", "weekdays": [7]}, headers=HEADERS)
    assert bad_day.status_code == 422
    bad_time = client.post("/routines", json={"title": "X", "weekdays": [1], "time": "25:00"}, headers=HEADERS)
    assert bad_time.status_code == 422
    cal = client.post("/calendars", json={"name": "Hols"}, headers=HEADERS).json()
    backwards = client.post(f"/calendars/{cal['id']}/periods",
                            json={"start_date": "2026-10-23", "end_date": "2026-10-19"}, headers=HEADERS)
    assert backwards.status_code == 422


def test_deleting_a_calendar_unpauses_its_routines(client):
    school, _ = setup_week(client)
    assert client.delete(f"/calendars/{school['id']}", headers=HEADERS).status_code == 204
    routines = client.get("/routines", headers=HEADERS).json()
    assert all(school["id"] not in r["paused_by"] for r in routines)
