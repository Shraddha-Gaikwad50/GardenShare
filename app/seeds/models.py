"""Pydantic schemas and category constants for the seed catalog."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SeedCategory(str, Enum):
    """High-level botanical groupings used in the community catalog."""

    VEGETABLE = "vegetable"
    HERB = "herb"
    FLOWER = "flower"
    FRUIT = "fruit"
    LEAFY_GREEN = "leafy_green"


ALLOWED_CATEGORIES = {item.value for item in SeedCategory}


class SeedCreate(BaseModel):
    """Payload for donating a new seed variety to the catalog."""

    name: str = Field(..., min_length=1, max_length=120)
    variety: str = Field(..., min_length=1, max_length=120)
    category: SeedCategory
    quantity: int = Field(..., ge=0)
    minimum_quantity: int = Field(default=0, ge=0)
    unit: str = Field(default="packet", min_length=1, max_length=40)


class SeedRead(BaseModel):
    """Public representation of a catalog seed and its on-hand stock."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    variety: str
    category: str
    quantity: int
    minimum_quantity: int
    reserved_quantity: int
    unit: str
    created_at: datetime


class InventoryAdjustment(BaseModel):
    """Payload for donating additional packets of an existing seed."""

    quantity: int = Field(..., gt=0)


class SeedPacketLabel(BaseModel):
    """Printed envelope label used at the seed-library desk.

    Label layout is unrelated to on-hand inventory accounting.
    """

    seed_id: int
    title: str
    season_hint: str
    category: str
