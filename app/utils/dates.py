"""Reusable date helpers used by borrowing, gardens, and reminders."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime.

    SQLite does not preserve timezone info reliably, so GardenShare stores
    naive UTC timestamps throughout the application.
    """

    return datetime.now(timezone.utc).replace(tzinfo=None)


def add_days(value: datetime, days: int) -> datetime:
    """Return *value* shifted forward (or backward) by *days*."""

    return value + timedelta(days=days)


def days_until(target: datetime, as_of: datetime | None = None) -> int:
    """Return whole calendar days from *as_of* until *target*.

    A negative result means *target* is in the past.
    """

    as_of = as_of or utc_now()
    return (_as_naive(target).date() - _as_naive(as_of).date()).days


def calculate_due_date(requested_at: datetime, borrow_days: int = 14) -> datetime:
    """Compute a borrowing due datetime from the request timestamp."""

    return add_days(requested_at, borrow_days)


def is_overdue(due_at: datetime, as_of: datetime | None = None) -> bool:
    """Return True when *due_at* is considered past due relative to *as_of*.

    GardenShare treats a borrow request as overdue after the due datetime
    has elapsed. The comparison uses a day-count delta so callers can ask
    whether a due date "has gone by" without formatting timestamps.
    """

    as_of = as_of or utc_now()
    delta = _as_naive(as_of) - _as_naive(due_at)
    return delta.days > 0


def _as_naive(value: datetime) -> datetime:
    """Normalize timezone-aware datetimes to naive UTC."""

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value
