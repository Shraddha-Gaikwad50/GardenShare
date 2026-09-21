"""Borrowing rules kept separate from request persistence.

Policies answer *whether* an action is allowed. ``service.py`` performs
the inventory mutations after a policy check succeeds.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from app.config.settings import get_settings
from app.database.models import BorrowRequest, Member
from app.members.service import InactiveMemberError
from app.utils.dates import calculate_due_date, is_overdue
from app.utils.validation import GardenShareError, validate_positive_quantity


class BorrowStatus(str, Enum):
    """Lifecycle states for a seed borrow request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"


class InvalidBorrowStateError(GardenShareError):
    """Raised when a request is not in the expected status."""

    status_code = 409


class SeedAlreadyReturnedError(GardenShareError):
    """Raised when a returned request is returned a second time."""

    status_code = 409


def assert_member_can_borrow(member: Member) -> None:
    """Active members may borrow; inactive members may not."""

    if not member.active:
        raise InactiveMemberError(f"member {member.id} is not active and cannot borrow seeds")


def assert_quantity_allowed(quantity: int) -> int:
    """Requested quantity must be positive and within the community cap."""

    cleaned = validate_positive_quantity(quantity, field_name="quantity")
    limit = get_settings().max_borrow_quantity
    if cleaned > limit:
        raise GardenShareError(f"quantity {cleaned} exceeds the maximum borrow of {limit}")
    return cleaned


def assert_request_pending(request: BorrowRequest) -> None:
    """Approvals and rejections apply only to pending requests."""

    if request.status != BorrowStatus.PENDING.value:
        raise InvalidBorrowStateError(
            f"borrow request {request.id} is '{request.status}', expected '{BorrowStatus.PENDING.value}'"
        )


def assert_request_approved_for_return(request: BorrowRequest) -> None:
    """Only an approved, not-yet-returned request can be returned."""

    if request.status == BorrowStatus.RETURNED.value or request.returned_at is not None:
        raise SeedAlreadyReturnedError(f"borrow request {request.id} has already been returned")
    if request.status != BorrowStatus.APPROVED.value:
        raise InvalidBorrowStateError(
            f"borrow request {request.id} is '{request.status}', expected '{BorrowStatus.APPROVED.value}'"
        )


def default_due_date(requested_at: datetime, borrow_days: int | None = None) -> datetime:
    """Compute the standard due datetime for a new borrow request."""

    days = borrow_days if borrow_days is not None else get_settings().default_borrow_days
    return calculate_due_date(requested_at, days)


def is_request_overdue(request: BorrowRequest, as_of: datetime | None = None) -> bool:
    """Return True for an approved, unreturned request that is past due."""

    if request.status != BorrowStatus.APPROVED.value:
        return False
    if request.returned_at is not None:
        return False
    return is_overdue(request.due_date, as_of)
