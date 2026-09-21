"""Pydantic schemas for garden plots and planting plans."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GardenPlotCreate(BaseModel):
    member_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=120)
    location: str = Field(..., min_length=1, max_length=255)
    size_sq_meters: float = Field(..., gt=0)


class GardenPlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    name: str
    location: str
    size_sq_meters: float


class GardenPlotAssign(BaseModel):
    member_id: int = Field(..., ge=1)


class PlantingPlanCreate(BaseModel):
    garden_plot_id: int = Field(..., ge=1)
    seed_id: int = Field(..., ge=1)
    planting_date: datetime
    status: str = Field(default="scheduled")


class PlantingPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    garden_plot_id: int
    seed_id: int
    planting_date: datetime
    expected_harvest_date: datetime
    status: str


class CompanionPlantingHint(BaseModel):
    """Informational companion-plant pairing used on plot signage.

    Companion planting advice is educational and does not change inventory
    or borrow request status.
    """

    crop: str
    companions: list[str]
    avoid: list[str]
