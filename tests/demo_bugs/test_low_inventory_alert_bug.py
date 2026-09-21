"""Documents the low-inventory alert defect at the minimum-quantity boundary."""

from __future__ import annotations

from app.notifications.reminders import build_low_inventory_alert
from app.seeds.catalog import add_seed
from app.seeds.inventory import check_inventory_threshold


def test_quantity_equal_to_minimum_is_low_stock(db) -> None:
    """Stock at the configured minimum should be treated as low inventory.

    Coordinators restock when available quantity is at or below minimum,
    not only when it has already dropped strictly below that number.
    """

    seed = add_seed(
        db,
        name="Lettuce",
        variety="Butterhead",
        category="leafy_green",
        quantity=4,
        minimum_quantity=4,
        unit="packet",
    )
    assert check_inventory_threshold(seed) is True
    alert = build_low_inventory_alert(seed)
    assert alert is not None
    assert "running low" in alert.subject.lower()
