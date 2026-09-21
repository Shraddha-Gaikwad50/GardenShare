"""Documents the inventory return defect: empty-shelf restock uses minimum quantity."""

from __future__ import annotations

from app.borrowing.service import approve_borrow_request, create_borrow_request, return_seed
from app.members.service import create_member
from app.seeds.catalog import add_seed


def test_returning_all_remaining_packets_restores_borrowed_quantity(db) -> None:
    """Full return of a depleting borrow should add back exactly what was borrowed.

    Setup: 5 packets on hand, minimum 8. Member borrows all 5 (shelf empty),
    then returns all 5. On-hand quantity should be 5 again.
    """

    member = create_member(db, "Alice Green", "alice@example.com")
    seed = add_seed(
        db,
        name="Tomato",
        variety="Cherry",
        category="vegetable",
        quantity=5,
        minimum_quantity=8,
        unit="packet",
    )
    request = create_borrow_request(db, member_id=member.id, seed_id=seed.id, quantity=5)
    approve_borrow_request(db, request.id)
    db.refresh(seed)
    assert seed.quantity == 0

    return_seed(db, request.id)
    db.refresh(seed)
    assert seed.quantity == 5
