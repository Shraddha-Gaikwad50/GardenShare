"""HTTP routes for member registration and directory lookup."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.members.models import MemberCreate, MemberDirectoryEntry, MemberRead
from app.members.service import (
    MemberService,
    build_membership_card_code,
    format_member_display_name,
    membership_anniversary_month,
)
from app.web import dump_models, html_or_json

router = APIRouter(prefix="/members", tags=["members"])


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def register_member(payload: MemberCreate, db: Session = Depends(get_db)) -> MemberRead:
    """Register a new community member."""

    member = MemberService(db).create_member(payload.name, payload.email)
    return MemberRead.model_validate(member)


@router.get("", response_model=None)
def list_registered_members(
    request: Request,
    active_only: bool = False,
    db: Session = Depends(get_db),
) -> HTMLResponse | JSONResponse:
    """List community members."""

    members = MemberService(db).list_members(active_only=active_only)
    payload = dump_models([MemberRead.model_validate(member) for member in members])
    rows = [
        {
            "id": member.id,
            "name": member.name,
            "email": member.email,
            "joined_at": member.joined_at,
            "active": member.active,
        }
        for member in members
    ]
    return html_or_json(
        request,
        payload,
        title="Members",
        subtitle="People registered in the community seed library.",
        columns=[
            ("id", "ID"),
            ("name", "Name"),
            ("email", "Email"),
            ("joined_at", "Joined"),
            ("active", "Active"),
        ],
        rows=rows,
    )


@router.get("/directory", response_model=list[MemberDirectoryEntry])
def membership_directory(db: Session = Depends(get_db)) -> list[MemberDirectoryEntry]:
    """Printed directory used at the community shed welcome desk.

    This endpoint is about names and membership cards, not seed stock.
    """

    members = MemberService(db).list_members()
    return [
        MemberDirectoryEntry(
            member_id=member.id,
            display_name=format_member_display_name(member.name),
            email=member.email,
            membership_card_code=build_membership_card_code(member),
            anniversary_month=membership_anniversary_month(member.joined_at),
        )
        for member in members
    ]


@router.get("/{member_id}", response_model=MemberRead)
def get_registered_member(member_id: int, db: Session = Depends(get_db)) -> MemberRead:
    """Fetch a single member by id."""

    member = MemberService(db).get_member(member_id)
    return MemberRead.model_validate(member)


@router.post("/{member_id}/deactivate", response_model=MemberRead)
def deactivate_registered_member(member_id: int, db: Session = Depends(get_db)) -> MemberRead:
    """Deactivate a member account."""

    member = MemberService(db).deactivate_member(member_id)
    return MemberRead.model_validate(member)
