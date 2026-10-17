"""Ranking rules. Plain code, no AI, so it is predictable and easy to test.

latest start = deadline - estimated duration - buffer(consequence)
"""

from datetime import datetime, timedelta

from .config import DEFAULT_CONSEQUENCE, DEFAULT_MINUTES
from .models import Task

BUFFERS = {
    1: timedelta(0),        # Trivial
    2: timedelta(0),        # Minor
    3: timedelta(hours=2),  # Moderate
    4: timedelta(days=1),   # Serious
    5: timedelta(days=2),   # Critical
}


def latest_start(task: Task) -> datetime | None:
    """When the task must be started to finish on time, with a safety buffer."""
    if task.deadline is None:
        return None
    minutes = task.estimated_minutes or DEFAULT_MINUTES
    consequence = task.consequence or DEFAULT_CONSEQUENCE
    return task.deadline - timedelta(minutes=minutes) - BUFFERS[consequence]


def build_board(tasks: list[Task], now: datetime) -> dict[str, list[Task]]:
    """Split open tasks into the sections the wall screen shows, each sorted.

    - overdue:    deadline has passed (most overdue first)
    - ranked:     has a deadline, sorted by latest start (ties: higher consequence first)
    - whenever:   no deadline (higher consequence first, then oldest first)
    - needs_info: a follow-up question was never answered
    """
    overdue, ranked, whenever, needs_info = [], [], [], []
    for task in tasks:
        if task.status == "done":
            continue
        if task.status == "needs_info":
            needs_info.append(task)
        elif task.deadline is None:
            whenever.append(task)
        elif task.deadline < now:
            overdue.append(task)
        else:
            ranked.append(task)

    overdue.sort(key=lambda t: t.deadline)
    ranked.sort(key=lambda t: (latest_start(t), -(t.consequence or DEFAULT_CONSEQUENCE)))
    whenever.sort(key=lambda t: (-(t.consequence or DEFAULT_CONSEQUENCE), t.created_at))
    needs_info.sort(key=lambda t: t.created_at)
    return {"overdue": overdue, "ranked": ranked, "whenever": whenever, "needs_info": needs_info}
