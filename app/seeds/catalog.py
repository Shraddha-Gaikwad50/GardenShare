"""Seed catalog search, listing, and variety lookup.

Catalog operations describe *what* seeds the community shares. Quantity
changes belong in ``inventory.py``.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Seed
from app.seeds.models import ALLOWED_CATEGORIES
from app.utils.dates import utc_now
from app.utils.validation import NotFoundError, ValidationError, validate_non_empty_string, validate_non_negative_int

logger = logging.getLogger(__name__)

PLANTING_SEASON_HINTS: dict[str, str] = {
    "tomato": "late spring after last frost",
    "carrot": "early spring or late summer",
    "basil": "warm soil in late spring",
    "lettuce": "cool weather, spring and fall",
    "marigold": "after frost, through summer",
}


class SeedNotFoundError(NotFoundError):
    """Raised when a seed id is missing from the catalog."""


def recommended_planting_season(seed_name: str) -> str:
    """Return a short seasonal hint for packet labels.

    This is printed on envelopes; it does not schedule garden plantings
    and does not change inventory counts.
    """

    return PLANTING_SEASON_HINTS.get(seed_name.strip().lower(), "see local frost dates")


def format_seed_packet_label(seed: Seed) -> str:
    """Build a human-readable packet title for the labeling drawer."""

    return f"{seed.name} — {seed.variety} ({seed.category})"


def add_seed(
    db: Session,
    *,
    name: str,
    variety: str,
    category: str,
    quantity: int,
    minimum_quantity: int = 0,
    unit: str = "packet",
) -> Seed:
    """Add a new seed variety to the community catalog."""

    cleaned_name = validate_non_empty_string(name, field_name="name")
    cleaned_variety = validate_non_empty_string(variety, field_name="variety")
    cleaned_category = validate_non_empty_string(category, field_name="category").lower()
    if cleaned_category not in ALLOWED_CATEGORIES:
        allowed = ", ".join(sorted(ALLOWED_CATEGORIES))
        raise ValidationError(f"category must be one of: {allowed}")
    validate_non_negative_int(quantity, field_name="quantity")
    validate_non_negative_int(minimum_quantity, field_name="minimum_quantity")
    cleaned_unit = validate_non_empty_string(unit, field_name="unit")

    seed = Seed(
        name=cleaned_name,
        variety=cleaned_variety,
        category=cleaned_category,
        quantity=quantity,
        minimum_quantity=minimum_quantity,
        reserved_quantity=0,
        unit=cleaned_unit,
        created_at=utc_now(),
    )
    db.add(seed)
    db.commit()
    db.refresh(seed)
    logger.info("Added catalog seed %s (%s / %s)", seed.id, seed.name, seed.variety)
    return seed


def get_seed(db: Session, seed_id: int) -> Seed:
    """Return a catalog seed by id."""

    seed = db.get(Seed, seed_id)
    if seed is None:
        raise SeedNotFoundError(f"seed {seed_id} was not found")
    return seed


def search_seeds(db: Session, query: str) -> list[Seed]:
    """Search catalog entries by name (case-insensitive substring)."""

    needle = validate_non_empty_string(query, field_name="q").lower()
    stmt = select(Seed).order_by(Seed.name, Seed.variety)
    return [seed for seed in db.scalars(stmt) if needle in seed.name.lower()]


def search_seeds_by_variety(db: Session, variety: str) -> list[Seed]:
    """Search catalog entries by variety name."""

    needle = validate_non_empty_string(variety, field_name="variety").lower()
    stmt = select(Seed).order_by(Seed.variety)
    return [seed for seed in db.scalars(stmt) if needle in seed.variety.lower()]


def filter_by_category(db: Session, category: str) -> list[Seed]:
    """Return seeds in a single catalog category."""

    cleaned = validate_non_empty_string(category, field_name="category").lower()
    if cleaned not in ALLOWED_CATEGORIES:
        allowed = ", ".join(sorted(ALLOWED_CATEGORIES))
        raise ValidationError(f"category must be one of: {allowed}")
    stmt = select(Seed).where(Seed.category == cleaned).order_by(Seed.name)
    return list(db.scalars(stmt))


def list_available_seeds(db: Session, *, in_stock_only: bool = False) -> list[Seed]:
    """List catalog seeds, optionally hiding fully depleted varieties."""

    stmt = select(Seed).order_by(Seed.name, Seed.variety)
    seeds = list(db.scalars(stmt))
    if in_stock_only:
        return [seed for seed in seeds if seed.quantity - seed.reserved_quantity > 0]
    return seeds


class SeedCatalog:
    """Catalog facade used by the seeds API layer."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add_seed(self, **kwargs) -> Seed:
        return add_seed(self.db, **kwargs)

    def get_seed(self, seed_id: int) -> Seed:
        return get_seed(self.db, seed_id)

    def search_seeds(self, query: str) -> list[Seed]:
        return search_seeds(self.db, query)

    def search_seeds_by_variety(self, variety: str) -> list[Seed]:
        return search_seeds_by_variety(self.db, variety)

    def filter_by_category(self, category: str) -> list[Seed]:
        return filter_by_category(self.db, category)

    def list_available_seeds(self, *, in_stock_only: bool = False) -> list[Seed]:
        return list_available_seeds(self.db, in_stock_only=in_stock_only)
