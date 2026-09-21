"""Garden plots, crop duration rules, and planting schedules.

Crop duration lives here so harvest estimates stay out of the HTTP layer
and out of the seed inventory module.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import GardenPlot, PlantingPlan
from app.members.service import get_member
from app.seeds.catalog import get_seed
from app.utils.dates import add_days, days_until, utc_now
from app.utils.validation import NotFoundError, ValidationError, validate_future_date, validate_non_empty_string

logger = logging.getLogger(__name__)

CROP_DURATION_DAYS: dict[str, int] = {
    "tomato": 80,
    "carrot": 70,
    "basil": 45,
    "lettuce": 40,
    "marigold": 60,
}

DEFAULT_CROP_DURATION_DAYS = 55

COMPANION_PLANTS: dict[str, dict[str, list[str]]] = {
    "tomato": {"companions": ["basil", "marigold"], "avoid": ["fennel"]},
    "carrot": {"companions": ["lettuce", "onion"], "avoid": ["dill"]},
    "basil": {"companions": ["tomato"], "avoid": []},
    "lettuce": {"companions": ["carrot", "radish"], "avoid": []},
    "marigold": {"companions": ["tomato"], "avoid": []},
}

ALLOWED_PLAN_STATUSES = {"scheduled", "planted", "harvested", "cancelled"}


class GardenPlotNotFoundError(NotFoundError):
    """Raised when a garden plot id does not exist."""


class PlantingPlanNotFoundError(NotFoundError):
    """Raised when a planting plan id does not exist."""


def crop_duration_days(seed_name: str) -> int:
    """Return expected days from planting to harvest for a crop name."""

    return CROP_DURATION_DAYS.get(seed_name.strip().lower(), DEFAULT_CROP_DURATION_DAYS)


def calculate_expected_harvest(seed_name: str, planting_date: datetime) -> datetime:
    """Compute harvest date from crop duration rules."""

    return add_days(planting_date, crop_duration_days(seed_name))


def companion_planting_for(seed_name: str) -> dict[str, list[str]]:
    """Return companion / avoid lists for plot signage (not scheduling)."""

    return COMPANION_PLANTS.get(
        seed_name.strip().lower(),
        {"companions": [], "avoid": []},
    )


def create_garden_plot(
    db: Session,
    *,
    member_id: int,
    name: str,
    location: str,
    size_sq_meters: float,
) -> GardenPlot:
    """Create a garden plot assigned to an existing member."""

    member = get_member(db, member_id)
    if size_sq_meters <= 0:
        raise ValidationError("size_sq_meters must be greater than zero")
    plot = GardenPlot(
        member_id=member.id,
        name=validate_non_empty_string(name, field_name="name"),
        location=validate_non_empty_string(location, field_name="location"),
        size_sq_meters=size_sq_meters,
    )
    db.add(plot)
    db.commit()
    db.refresh(plot)
    logger.info("Created garden plot %s for member %s", plot.id, member.id)
    return plot


def list_garden_plots(db: Session, member_id: int | None = None) -> list[GardenPlot]:
    """List garden plots, optionally filtered by member."""

    stmt = select(GardenPlot).order_by(GardenPlot.id)
    if member_id is not None:
        stmt = stmt.where(GardenPlot.member_id == member_id)
    return list(db.scalars(stmt))


def get_garden_plot(db: Session, plot_id: int) -> GardenPlot:
    """Return a garden plot by id."""

    plot = db.get(GardenPlot, plot_id)
    if plot is None:
        raise GardenPlotNotFoundError(f"garden plot {plot_id} was not found")
    return plot


def assign_plot_member(db: Session, plot_id: int, member_id: int) -> GardenPlot:
    """Reassign an existing plot to a different member."""

    plot = get_garden_plot(db, plot_id)
    member = get_member(db, member_id)
    plot.member_id = member.id
    db.commit()
    db.refresh(plot)
    logger.info("Assigned garden plot %s to member %s", plot.id, member.id)
    return plot


def create_planting_plan(
    db: Session,
    *,
    garden_plot_id: int,
    seed_id: int,
    planting_date: datetime,
    status: str = "scheduled",
) -> PlantingPlan:
    """Schedule a planting in a plot and compute the expected harvest date."""

    plot = get_garden_plot(db, garden_plot_id)
    seed = get_seed(db, seed_id)
    validate_future_date(planting_date, allow_today=True)
    cleaned_status = status.strip().lower()
    if cleaned_status not in ALLOWED_PLAN_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_PLAN_STATUSES))
        raise ValidationError(f"status must be one of: {allowed}")

    plan = PlantingPlan(
        garden_plot_id=plot.id,
        seed_id=seed.id,
        planting_date=planting_date,
        expected_harvest_date=calculate_expected_harvest(seed.name, planting_date),
        status=cleaned_status,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    logger.info("Created planting plan %s for plot %s / seed %s", plan.id, plot.id, seed.id)
    return plan


def get_upcoming_plantings(db: Session, as_of: datetime | None = None) -> list[PlantingPlan]:
    """Return scheduled plantings on or after *as_of* (defaults to now)."""

    as_of = as_of or utc_now()
    stmt = (
        select(PlantingPlan)
        .where(PlantingPlan.status == "scheduled")
        .order_by(PlantingPlan.planting_date)
    )
    return [plan for plan in db.scalars(stmt) if days_until(plan.planting_date, as_of) >= 0]


class GardenPlanner:
    """Facade for plot management and planting schedules."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_garden_plot(self, member_id: int, name: str, location: str, size_sq_meters: float) -> GardenPlot:
        return create_garden_plot(
            self.db,
            member_id=member_id,
            name=name,
            location=location,
            size_sq_meters=size_sq_meters,
        )

    def list_garden_plots(self, member_id: int | None = None) -> list[GardenPlot]:
        return list_garden_plots(self.db, member_id=member_id)

    def assign_plot_member(self, plot_id: int, member_id: int) -> GardenPlot:
        return assign_plot_member(self.db, plot_id, member_id)

    def create_planting_plan(
        self,
        garden_plot_id: int,
        seed_id: int,
        planting_date: datetime,
        status: str = "scheduled",
    ) -> PlantingPlan:
        return create_planting_plan(
            self.db,
            garden_plot_id=garden_plot_id,
            seed_id=seed_id,
            planting_date=planting_date,
            status=status,
        )

    def get_upcoming_plantings(self) -> list[PlantingPlan]:
        return get_upcoming_plantings(self.db)

    def calculate_expected_harvest(self, seed_name: str, planting_date: datetime) -> datetime:
        return calculate_expected_harvest(seed_name, planting_date)
