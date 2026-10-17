from datetime import datetime, timedelta

from app.models import Task
from app.ranking import build_board, latest_start

NOW = datetime(2026, 10, 12, 9, 0)  # a Monday, naive UTC


def make(id, deadline=None, minutes=30, consequence=3, status="active", created=NOW):
    return Task(
        id=id, raw_input="", title=f"t{id}", deadline=deadline, estimated_minutes=minutes,
        consequence=consequence, status=status, created_at=created, clarifications=[],
    )


def test_latest_start_subtracts_duration_and_buffer():
    deadline = datetime(2026, 10, 16, 17, 0)
    assert latest_start(make(1, deadline, minutes=60, consequence=1)) == deadline - timedelta(hours=1)
    assert latest_start(make(2, deadline, minutes=60, consequence=3)) == deadline - timedelta(hours=3)
    assert latest_start(make(3, deadline, minutes=60, consequence=4)) == deadline - timedelta(days=1, hours=1)
    assert latest_start(make(4, deadline, minutes=60, consequence=5)) == deadline - timedelta(days=2, hours=1)


def test_long_task_due_later_can_outrank_short_task_due_sooner():
    short_thursday = make(1, datetime(2026, 10, 15, 17), minutes=5, consequence=2)
    long_friday = make(2, datetime(2026, 10, 16, 17), minutes=180, consequence=4)  # start by Thu 14:00
    board = build_board([short_thursday, long_friday], NOW)
    assert [t.id for t in board["ranked"]] == [2, 1]


def test_tasks_are_split_into_sections():
    tasks = [
        make(1, NOW - timedelta(hours=1)),           # overdue
        make(2, NOW + timedelta(days=1)),            # ranked
        make(3, None, consequence=2),                # whenever
        make(4, None, consequence=5),                # whenever, higher consequence
        make(5, None, status="needs_info"),          # needs info
        make(6, NOW + timedelta(days=1), status="done"),
    ]
    board = build_board(tasks, NOW)
    assert [t.id for t in board["overdue"]] == [1]
    assert [t.id for t in board["ranked"]] == [2]
    assert [t.id for t in board["whenever"]] == [4, 3]
    assert [t.id for t in board["needs_info"]] == [5]
