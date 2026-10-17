"""Time helpers.

All datetimes are stored in the database as UTC without tzinfo ("naive UTC"),
because SQLite has no time zone support. These helpers convert at the edges.
"""

from datetime import datetime, timezone

from .config import APP_TIMEZONE


def utcnow() -> datetime:
    """Current time as naive UTC (the storage format)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_storage(dt: datetime) -> datetime:
    """Convert any datetime to naive UTC. Naive input is treated as local time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=APP_TIMEZONE)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def from_storage(dt: datetime | None) -> datetime | None:
    """Turn stored naive UTC into an aware UTC datetime for API output."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc)


def to_local(dt: datetime) -> datetime:
    """Stored naive UTC -> aware local time (for messages Siri reads out)."""
    return dt.replace(tzinfo=timezone.utc).astimezone(APP_TIMEZONE)


def spoken(dt: datetime) -> str:
    """e.g. 'Friday 17 October at 17:00' for Siri to read out."""
    local = to_local(dt)
    return f"{local:%A} {local.day} {local:%B} at {local:%H:%M}"
