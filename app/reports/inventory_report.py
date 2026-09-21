"""Inventory summary and low-stock reports.

These reports describe catalog quantities. They do not schedule plantings
or register members.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.seeds.catalog import list_available_seeds
from app.seeds.inventory import check_inventory_threshold, get_available_quantity
from app.utils.dates import utc_now


def generate_inventory_report(db: Session) -> dict:
    """Return a structured summary of every catalog seed."""

    seeds = list_available_seeds(db)
    items = []
    total_available = 0
    for seed in seeds:
        available = get_available_quantity(seed)
        total_available += available
        items.append(
            {
                "seed_id": seed.id,
                "name": seed.name,
                "variety": seed.variety,
                "category": seed.category,
                "quantity": seed.quantity,
                "reserved_quantity": seed.reserved_quantity,
                "available_quantity": available,
                "minimum_quantity": seed.minimum_quantity,
                "unit": seed.unit,
                "is_low_stock": check_inventory_threshold(seed),
            }
        )
    return {
        "generated_at": utc_now().isoformat(sep=" "),
        "seed_count": len(items),
        "total_available": total_available,
        "items": items,
    }


def generate_low_stock_report(db: Session) -> dict:
    """Return only seeds that are below the configured minimum quantity."""

    summary = generate_inventory_report(db)
    low_items = [item for item in summary["items"] if item["is_low_stock"]]
    return {
        "generated_at": summary["generated_at"],
        "low_stock_count": len(low_items),
        "items": low_items,
    }
