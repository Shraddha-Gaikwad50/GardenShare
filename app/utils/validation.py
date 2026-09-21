"""Shared validation helpers and application error types."""

from __future__ import annotations

import re
from datetime import datetime

from app.utils.dates import utc_now

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class GardenShareError(Exception):
    """Base class for recoverable GardenShare business errors."""

    status_code = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ValidationError(GardenShareError):
    """Raised when a caller-supplied value is not acceptable."""

    status_code = 422


class NotFoundError(GardenShareError):
    """Raised when a requested record does not exist."""

    status_code = 404


class ConflictError(GardenShareError):
    """Raised when an operation conflicts with current state."""

    status_code = 409


def validate_positive_quantity(quantity: int, *, field_name: str = "quantity") -> int:
    """Require a strictly positive integer quantity."""

    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise ValidationError(f"{field_name} must be an integer")
    if quantity <= 0:
        raise ValidationError(f"{field_name} must be greater than zero")
    return quantity


def validate_non_empty_string(value: str, *, field_name: str = "value") -> str:
    """Require a stripped, non-empty string."""

    if value is None:
        raise ValidationError(f"{field_name} is required")
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} must not be empty")
    return cleaned


def validate_email(email: str) -> str:
    """Normalize and validate an email address."""

    cleaned = validate_non_empty_string(email, field_name="email").lower()
    if not EMAIL_PATTERN.match(cleaned):
        raise ValidationError(f"invalid email address: {email}")
    return cleaned


def validate_future_date(value: datetime, *, allow_today: bool = True) -> datetime:
    """Require *value* to be today or in the future."""

    now = utc_now()
    if allow_today:
        if value.date() < now.date():
            raise ValidationError("date must not be in the past")
    elif value <= now:
        raise ValidationError("date must be in the future")
    return value


def validate_non_negative_int(value: int, *, field_name: str = "value") -> int:
    """Require an integer that is zero or greater."""

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer")
    if value < 0:
        raise ValidationError(f"{field_name} must not be negative")
    return value
