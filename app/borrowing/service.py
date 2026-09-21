"""Borrowing workflow: request, approve, reject, return, and overdue lookup.

Approved borrowing decreases available seed inventory. Returning seeds
increases inventory. Rejected requests must not change on-hand stock.
"""

# Demo change for incremental indexing validation
# Real GitHub webhook indexing test

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.borrowing.policies import (
    BorrowStatus,
    assert_member_can_borrow,
    assert_quantity_allowed,
    assert_request_approved_for_return,
    assert_request_pending,
    default_due_date,
    is_request_overdue,
)
from app.database.models import BorrowRequest
from app.members.service import require_active_member
from app.seeds.catalog import get_seed
from app.seeds.inventory import (
    decrease_inventory,
    release_inventory,
    reserve_inventory,
    restore_borrowed_quantity,
)
from app.utils.dates import utc_now
from app.utils.validation import NotFoundError

logger = logging.getLogger(__name__)


class BorrowRequestNotFoundError(NotFoundError):
    """Raised when a borrow request id does not exist."""


def create_borrow_request(
    db: Session,
    *,
    member_id: int,
    seed_id: int,
    quantity: int,
    borrow_days: int | None = None,
) -> BorrowRequest:
    """Create a pending borrow request and reserve inventory."""

    member = require_active_member(db, member_id)
    assert_member_can_borrow(member)
    amount = assert_quantity_allowed(quantity)
    seed = get_seed(db, seed_id)

    reserve_inventory(db, seed.id, amount)

    requested_at = utc_now()
    request = BorrowRequest(
        member_id=member.id,
        seed_id=seed.id,
        quantity=amount,
        requested_at=requested_at,
        due_date=default_due_date(requested_at, borrow_days),
        returned_at=None,
        status=BorrowStatus.PENDING.value,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    logger.info(
        "Created borrow request %s: member %s reserved %s of seed %s",
        request.id,
        member.id,
        amount,
        seed.id,
    )
    return request


def approve_borrow_request(db: Session, request_id: int) -> BorrowRequest:
    """Approve a pending request: release the hold and decrease on-hand stock."""

    request = get_borrow_request(db, request_id)
    assert_request_pending(request)
    release_inventory(db, request.seed_id, request.quantity)
    decrease_inventory(db, request.seed_id, request.quantity)
    request.status = BorrowStatus.APPROVED.value
    db.commit()
    db.refresh(request)
    logger.info("Approved borrow request %s", request.id)
    return request


def reject_borrow_request(db: Session, request_id: int) -> BorrowRequest:
    """Reject a pending request and release reserved inventory unchanged."""

    request = get_borrow_request(db, request_id)
    assert_request_pending(request)
    release_inventory(db, request.seed_id, request.quantity)
    request.status = BorrowStatus.REJECTED.value
    db.commit()
    db.refresh(request)
    logger.info("Rejected borrow request %s", request.id)
    return request


def return_seed(db: Session, request_id: int) -> BorrowRequest:
    """Record a full return of borrowed seeds and restore inventory."""

    request = get_borrow_request(db, request_id)
    assert_request_approved_for_return(request)
    restore_borrowed_quantity(db, request.seed_id, request.quantity)
    request.returned_at = utc_now()
    request.status = BorrowStatus.RETURNED.value
    db.commit()
    db.refresh(request)
    logger.info("Returned borrow request %s", request.id)
    return request


def get_borrow_request(db: Session, request_id: int) -> BorrowRequest:
    """Load a borrow request by id."""

    request = db.get(BorrowRequest, request_id)
    if request is None:
        raise BorrowRequestNotFoundError(f"borrow request {request_id} was not found")
    return request


def get_active_borrow_requests(db: Session) -> list[BorrowRequest]:
    """Return approved requests that have not yet been returned."""

    stmt = (
        select(BorrowRequest)
        .where(BorrowRequest.status == BorrowStatus.APPROVED.value)
        .where(BorrowRequest.returned_at.is_(None))
        .order_by(BorrowRequest.due_date)
    )
    return list(db.scalars(stmt))


def get_overdue_requests(db: Session, as_of=None) -> list[BorrowRequest]:
    """Return active borrow requests whose due date has passed."""

    return [request for request in get_active_borrow_requests(db) if is_request_overdue(request, as_of)]


class BorrowingService:
    """Service facade for the seed borrowing workflow."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_borrow_request(self, member_id: int, seed_id: int, quantity: int) -> BorrowRequest:
        return create_borrow_request(self.db, member_id=member_id, seed_id=seed_id, quantity=quantity)

    def approve_borrow_request(self, request_id: int) -> BorrowRequest:
        return approve_borrow_request(self.db, request_id)

    def reject_borrow_request(self, request_id: int) -> BorrowRequest:
        return reject_borrow_request(self.db, request_id)

    def return_seed(self, request_id: int) -> BorrowRequest:
        return return_seed(self.db, request_id)

    def get_active_borrow_requests(self) -> list[BorrowRequest]:
        return get_active_borrow_requests(self.db)

    def get_overdue_requests(self) -> list[BorrowRequest]:
        return get_overdue_requests(self.db)
