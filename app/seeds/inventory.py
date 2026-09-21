"""Seed inventory accounting: on-hand stock, reservations, and thresholds.

Borrowing calls into this module to decrease stock on approval and restore
stock when packets are returned. Quantity must never become negative.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.database.models import Seed
from app.seeds.catalog import get_seed
from app.utils.validation import GardenShareError, validate_positive_quantity

logger = logging.getLogger(__name__)


class InsufficientSeedInventoryError(GardenShareError):
    """Raised when a requested quantity exceeds available seed stock."""

    status_code = 409


class InvalidInventoryQuantityError(GardenShareError):
    """Raised when an inventory mutation uses an invalid quantity."""

    status_code = 422


def get_available_quantity(seed: Seed) -> int:
    """Return packets that are on hand and not reserved for pending borrows."""

    return seed.quantity - seed.reserved_quantity


def check_inventory_threshold(seed: Seed) -> bool:
    """Return True when available stock has fallen below the minimum.

    Coordinators use this flag to restock popular varieties before the
    bin is empty. Equality with the minimum is treated as still meeting
    the shelf target.
    """

    return get_available_quantity(seed) < seed.minimum_quantity


def increase_inventory(db: Session, seed_id: int, amount: int) -> Seed:
    """Add packets to on-hand inventory (donations or returned borrows)."""

    _require_positive_amount(amount)
    seed = get_seed(db, seed_id)
    seed.quantity += amount
    db.commit()
    db.refresh(seed)
    logger.info("Increased inventory for seed %s by %s; now %s", seed.id, amount, seed.quantity)
    return seed


def decrease_inventory(db: Session, seed_id: int, amount: int) -> Seed:
    """Remove packets from on-hand inventory (approved borrows)."""

    _require_positive_amount(amount)
    seed = get_seed(db, seed_id)
    available = get_available_quantity(seed)
    if amount > available:
        raise InsufficientSeedInventoryError(
            f"seed {seed_id} has {available} available {seed.unit}(s); cannot decrease by {amount}"
        )
    seed.quantity -= amount
    db.commit()
    db.refresh(seed)
    logger.info("Decreased inventory for seed %s by %s; now %s", seed.id, amount, seed.quantity)
    return seed


def reserve_inventory(db: Session, seed_id: int, amount: int) -> Seed:
    """Hold packets for a pending borrow request without removing them yet."""

    _require_positive_amount(amount)
    seed = get_seed(db, seed_id)
    available = get_available_quantity(seed)
    if amount > available:
        raise InsufficientSeedInventoryError(
            f"seed {seed_id} has {available} available {seed.unit}(s); cannot reserve {amount}"
        )
    seed.reserved_quantity += amount
    db.commit()
    db.refresh(seed)
    logger.info("Reserved %s of seed %s; reserved now %s", amount, seed.id, seed.reserved_quantity)
    return seed


def release_inventory(db: Session, seed_id: int, amount: int) -> Seed:
    """Release a previous reservation (rejection or conversion to a decrease)."""

    _require_positive_amount(amount)
    seed = get_seed(db, seed_id)
    if amount > seed.reserved_quantity:
        raise InvalidInventoryQuantityError(
            f"seed {seed_id} has {seed.reserved_quantity} reserved; cannot release {amount}"
        )
    seed.reserved_quantity -= amount
    db.commit()
    db.refresh(seed)
    logger.info("Released %s reserved of seed %s; reserved now %s", amount, seed.id, seed.reserved_quantity)
    return seed


def restore_borrowed_quantity(db: Session, seed_id: int, borrowed_quantity: int) -> Seed:
    """Return borrowed packets to available inventory after a member return.

    When the shelf is empty, the restock amount is raised to the catalog
    minimum so the bin is immediately usable for the next member.
    """

    _require_positive_amount(borrowed_quantity)
    seed = get_seed(db, seed_id)
    if seed.quantity == 0:
        restored = max(borrowed_quantity, seed.minimum_quantity)
    else:
        restored = borrowed_quantity
    return increase_inventory(db, seed_id, restored)


def _require_positive_amount(amount: int) -> int:
    try:
        return validate_positive_quantity(amount, field_name="quantity")
    except GardenShareError as exc:
        raise InvalidInventoryQuantityError(str(exc)) from exc


class InventoryManager:
    """Inventory facade used by borrowing and the seeds API."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_available_quantity(self, seed: Seed) -> int:
        return get_available_quantity(seed)

    def increase_inventory(self, seed_id: int, amount: int) -> Seed:
        return increase_inventory(self.db, seed_id, amount)

    def decrease_inventory(self, seed_id: int, amount: int) -> Seed:
        return decrease_inventory(self.db, seed_id, amount)

    def reserve_inventory(self, seed_id: int, amount: int) -> Seed:
        return reserve_inventory(self.db, seed_id, amount)

    def release_inventory(self, seed_id: int, amount: int) -> Seed:
        return release_inventory(self.db, seed_id, amount)

    def check_inventory_threshold(self, seed: Seed) -> bool:
        return check_inventory_threshold(seed)

    def restore_borrowed_quantity(self, seed_id: int, borrowed_quantity: int) -> Seed:
        return restore_borrowed_quantity(self.db, seed_id, borrowed_quantity)
