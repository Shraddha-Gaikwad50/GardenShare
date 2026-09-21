"""Member registration, lookup, and community identity helpers.

This module is intentionally about people, not seed inventory. Inventory
adjustments and borrow approvals live in the seeds and borrowing packages.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Member
from app.utils.dates import utc_now
from app.utils.validation import (
    ConflictError,
    GardenShareError,
    NotFoundError,
    validate_email,
    validate_non_empty_string,
)

logger = logging.getLogger(__name__)


class MemberNotFoundError(NotFoundError):
    """Raised when a member id does not exist."""


class DuplicateMemberEmailError(ConflictError):
    """Raised when registering an email that is already in use."""


class InactiveMemberError(GardenShareError):
    """Raised when an inactive member attempts a restricted action."""

    status_code = 403


def validate_member_email(email: str) -> str:
    """Validate and normalize a member email address."""

    return validate_email(email)


def format_member_display_name(name: str) -> str:
    """Return a directory-friendly display name.

    Used by the printed membership booklet and welcome letters. This does
    not affect borrowing or seed inventory.
    """

    cleaned = validate_non_empty_string(name, field_name="name")
    return " ".join(part.capitalize() for part in cleaned.split())


def build_membership_card_code(member: Member) -> str:
    """Build a stable, non-secret community membership card code.

    The code is derived from the member id and email so greeters can look
    up a person at the tool shed. It is not an authentication credential.
    """

    basis = f"{member.id}:{member.email}".encode("utf-8")
    digest = hashlib.sha256(basis).hexdigest()[:10].upper()
    return f"GS-{member.id:04d}-{digest}"


def membership_anniversary_month(joined_at: datetime) -> int:
    """Return the calendar month of a member's join anniversary."""

    return joined_at.month


def create_member(db: Session, name: str, email: str) -> Member:
    """Register a new active community member."""

    display_name = format_member_display_name(name)
    normalized_email = validate_member_email(email)

    existing = db.scalar(select(Member).where(Member.email == normalized_email))
    if existing is not None:
        raise DuplicateMemberEmailError(f"email already registered: {normalized_email}")

    member = Member(
        name=display_name,
        email=normalized_email,
        joined_at=utc_now(),
        active=True,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    logger.info("Registered member %s (%s)", member.id, member.email)
    return member


def get_member(db: Session, member_id: int) -> Member:
    """Return a member by id or raise MemberNotFoundError."""

    member = db.get(Member, member_id)
    if member is None:
        raise MemberNotFoundError(f"member {member_id} was not found")
    return member


def list_members(db: Session, *, active_only: bool = False) -> list[Member]:
    """Return members, optionally restricted to active accounts."""

    stmt = select(Member).order_by(Member.id)
    if active_only:
        stmt = stmt.where(Member.active.is_(True))
    return list(db.scalars(stmt))


def deactivate_member(db: Session, member_id: int) -> Member:
    """Mark a member inactive so they can no longer borrow seeds."""

    member = get_member(db, member_id)
    member.active = False
    db.commit()
    db.refresh(member)
    logger.info("Deactivated member %s", member.id)
    return member


def require_active_member(db: Session, member_id: int) -> Member:
    """Return an active member or raise InactiveMemberError."""

    member = get_member(db, member_id)
    if not member.active:
        raise InactiveMemberError(f"member {member_id} is not active")
    return member


class MemberService:
    """Service facade for member registration and directory operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_member(self, name: str, email: str) -> Member:
        return create_member(self.db, name, email)

    def get_member(self, member_id: int) -> Member:
        return get_member(self.db, member_id)

    def list_members(self, *, active_only: bool = False) -> list[Member]:
        return list_members(self.db, active_only=active_only)

    def deactivate_member(self, member_id: int) -> Member:
        return deactivate_member(self.db, member_id)

    def validate_member_email(self, email: str) -> str:
        return validate_member_email(email)
