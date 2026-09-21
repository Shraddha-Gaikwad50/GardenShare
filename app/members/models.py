"""Pydantic schemas for member registration and directory responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemberCreate(BaseModel):
    """Payload for registering a new community member."""

    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=255)


class MemberRead(BaseModel):
    """Public representation of a community member."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    joined_at: datetime
    active: bool


class MemberDirectoryEntry(BaseModel):
    """Printed-directory row: name formatting only, not inventory related."""

    member_id: int
    display_name: str
    email: str
    membership_card_code: str
    anniversary_month: int
