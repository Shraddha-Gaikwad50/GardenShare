"""Documents the overdue boundary defect: same-day past-due is not detected."""

from __future__ import annotations

from datetime import timedelta

from app.borrowing.service import approve_borrow_request, create_borrow_request, get_overdue_requests
from app.members.service import create_member
from app.seeds.catalog import add_seed
from app.utils.dates import is_overdue, utc_now


def test_request_due_earlier_today_is_overdue(db) -> None:
    """A request whose due datetime is already in the past should be overdue.

    Waiting a full extra 24 hours after the due datetime should not be required.
    """

    member = create_member(db, "Ravi Kumar", "ravi@example.com")
    seed = add_seed(
        db,
        name="Basil",
        variety="Genovese",
        category="herb",
        quantity=6,
        minimum_quantity=2,
    )
    request = create_borrow_request(db, member_id=member.id, seed_id=seed.id, quantity=1)
    approve_borrow_request(db, request.id)

    now = utc_now()
    request.due_date = now - timedelta(hours=3)
    db.commit()

    assert is_overdue(request.due_date, as_of=now) is True
    overdue = get_overdue_requests(db, as_of=now)
    assert [item.id for item in overdue] == [request.id]
