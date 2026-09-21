"""Member registration and validation tests."""

from __future__ import annotations

import pytest

from app.members.service import (
    DuplicateMemberEmailError,
    MemberNotFoundError,
    create_member,
    deactivate_member,
    get_member,
    list_members,
    validate_member_email,
)
from app.utils.validation import ValidationError


def test_create_member(db) -> None:
    member = create_member(db, "ravi kumar", "Ravi.Kumar@Example.com")
    assert member.id is not None
    assert member.name == "Ravi Kumar"
    assert member.email == "ravi.kumar@example.com"
    assert member.active is True


def test_validate_member_email_accepts_normal_address() -> None:
    assert validate_member_email("Maya.Shah@community.org") == "maya.shah@community.org"


def test_validate_member_email_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        validate_member_email("not-an-email")


def test_duplicate_email_is_rejected(db) -> None:
    create_member(db, "Alice Green", "alice@example.com")
    with pytest.raises(DuplicateMemberEmailError):
        create_member(db, "Alice Two", "alice@example.com")


def test_get_member_and_list(db) -> None:
    first = create_member(db, "Alice Green", "alice@example.com")
    create_member(db, "Maya Shah", "maya@example.com")
    loaded = get_member(db, first.id)
    assert loaded.email == "alice@example.com"
    assert len(list_members(db)) == 2


def test_get_missing_member_raises(db) -> None:
    with pytest.raises(MemberNotFoundError):
        get_member(db, 999)


def test_deactivate_member(db) -> None:
    member = create_member(db, "Alice Green", "alice@example.com")
    updated = deactivate_member(db, member.id)
    assert updated.active is False


def test_register_member_via_api(client) -> None:
    response = client.post("/members", json={"name": "Maya Shah", "email": "maya@example.com"})
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "maya@example.com"
    fetched = client.get(f"/members/{body['id']}")
    assert fetched.status_code == 200
    listed = client.get("/members")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    deactivated = client.post(f"/members/{body['id']}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False
