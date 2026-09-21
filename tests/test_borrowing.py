"""Borrowing workflow tests."""

from __future__ import annotations

import pytest

from app.borrowing.policies import BorrowStatus, SeedAlreadyReturnedError
from app.borrowing.service import (
    approve_borrow_request,
    create_borrow_request,
    get_active_borrow_requests,
    get_overdue_requests,
    reject_borrow_request,
    return_seed,
)
from app.members.service import InactiveMemberError, create_member, deactivate_member
from app.seeds.catalog import add_seed
from app.seeds.inventory import get_available_quantity
from app.utils.dates import add_days, utc_now


def test_create_and_approve_borrow_decreases_inventory(db, member, tomato) -> None:
    request = create_borrow_request(db, member_id=member.id, seed_id=tomato.id, quantity=3)
    assert request.status == BorrowStatus.PENDING.value
    db.refresh(tomato)
    assert tomato.reserved_quantity == 3
    assert get_available_quantity(tomato) == 7

    approved = approve_borrow_request(db, request.id)
    db.refresh(tomato)
    assert approved.status == BorrowStatus.APPROVED.value
    assert tomato.quantity == 7
    assert tomato.reserved_quantity == 0


def test_reject_does_not_change_on_hand_inventory(db, member, tomato) -> None:
    request = create_borrow_request(db, member_id=member.id, seed_id=tomato.id, quantity=2)
    reject_borrow_request(db, request.id)
    db.refresh(tomato)
    assert tomato.quantity == 10
    assert tomato.reserved_quantity == 0


def test_return_restores_inventory_when_stock_remains(db, member, tomato) -> None:
    request = create_borrow_request(db, member_id=member.id, seed_id=tomato.id, quantity=3)
    approve_borrow_request(db, request.id)
    returned = return_seed(db, request.id)
    db.refresh(tomato)
    assert returned.status == BorrowStatus.RETURNED.value
    assert tomato.quantity == 10


def test_cannot_return_twice(db, member, tomato) -> None:
    request = create_borrow_request(db, member_id=member.id, seed_id=tomato.id, quantity=1)
    approve_borrow_request(db, request.id)
    return_seed(db, request.id)
    with pytest.raises(SeedAlreadyReturnedError):
        return_seed(db, request.id)


def test_inactive_member_cannot_borrow(db, tomato) -> None:
    member = create_member(db, "Maya Shah", "maya@example.com")
    deactivate_member(db, member.id)
    with pytest.raises(InactiveMemberError):
        create_borrow_request(db, member_id=member.id, seed_id=tomato.id, quantity=1)


def test_overdue_requests_include_due_dates_several_days_ago(db, member, tomato) -> None:
    request = create_borrow_request(db, member_id=member.id, seed_id=tomato.id, quantity=1)
    approve_borrow_request(db, request.id)
    request.due_date = add_days(utc_now(), -3)
    db.commit()
    overdue = get_overdue_requests(db)
    assert len(overdue) == 1
    assert overdue[0].id == request.id


def test_active_requests_exclude_returned(db, member, tomato) -> None:
    request = create_borrow_request(db, member_id=member.id, seed_id=tomato.id, quantity=1)
    approve_borrow_request(db, request.id)
    assert len(get_active_borrow_requests(db)) == 1
    return_seed(db, request.id)
    assert get_active_borrow_requests(db) == []


def test_borrow_api_flow(client) -> None:
    member = client.post("/members", json={"name": "Ravi Kumar", "email": "ravi@example.com"}).json()
    seed = client.post(
        "/seeds",
        json={
            "name": "Basil",
            "variety": "Genovese",
            "category": "herb",
            "quantity": 6,
            "minimum_quantity": 2,
        },
    ).json()
    created = client.post(
        "/borrow-requests",
        json={"member_id": member["id"], "seed_id": seed["id"], "quantity": 2},
    )
    assert created.status_code == 201
    request_id = created.json()["id"]
    approved = client.post(f"/borrow-requests/{request_id}/approve")
    assert approved.status_code == 200
    returned = client.post(f"/borrow-requests/{request_id}/return")
    assert returned.json()["status"] == "returned"
