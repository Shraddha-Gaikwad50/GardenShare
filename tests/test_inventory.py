"""Seed catalog and inventory tests."""

from __future__ import annotations

import pytest

from app.seeds.catalog import add_seed, filter_by_category, search_seeds, search_seeds_by_variety
from app.seeds.inventory import (
    InsufficientSeedInventoryError,
    InvalidInventoryQuantityError,
    check_inventory_threshold,
    decrease_inventory,
    get_available_quantity,
    increase_inventory,
    release_inventory,
    reserve_inventory,
)


def test_add_and_search_seeds(db) -> None:
    add_seed(db, name="Tomato", variety="Cherry", category="vegetable", quantity=12, minimum_quantity=4)
    add_seed(db, name="Basil", variety="Genovese", category="herb", quantity=8, minimum_quantity=3)
    matches = search_seeds(db, "tom")
    assert len(matches) == 1
    assert matches[0].name == "Tomato"
    varieties = search_seeds_by_variety(db, "geno")
    assert varieties[0].variety == "Genovese"
    herbs = filter_by_category(db, "herb")
    assert len(herbs) == 1


def test_inventory_increase_and_decrease(db, tomato) -> None:
    increased = increase_inventory(db, tomato.id, 5)
    assert increased.quantity == 15
    decreased = decrease_inventory(db, tomato.id, 3)
    assert decreased.quantity == 12
    assert get_available_quantity(decreased) == 12


def test_inventory_cannot_go_negative(db, tomato) -> None:
    with pytest.raises(InsufficientSeedInventoryError):
        decrease_inventory(db, tomato.id, 50)


def test_inventory_rejects_zero_or_negative_amount(db, tomato) -> None:
    with pytest.raises(InvalidInventoryQuantityError):
        increase_inventory(db, tomato.id, 0)
    with pytest.raises(InvalidInventoryQuantityError):
        decrease_inventory(db, tomato.id, -2)


def test_reserve_and_release_inventory(db, tomato) -> None:
    reserved = reserve_inventory(db, tomato.id, 4)
    assert reserved.reserved_quantity == 4
    assert get_available_quantity(reserved) == 6
    with pytest.raises(InsufficientSeedInventoryError):
        reserve_inventory(db, tomato.id, 7)
    released = release_inventory(db, tomato.id, 4)
    assert released.reserved_quantity == 0


def test_low_stock_when_strictly_below_minimum(db) -> None:
    seed = add_seed(
        db,
        name="Carrot",
        variety="Nantes",
        category="vegetable",
        quantity=3,
        minimum_quantity=5,
    )
    assert check_inventory_threshold(seed) is True
    restocked = increase_inventory(db, seed.id, 4)
    assert check_inventory_threshold(restocked) is False


def test_seed_api_create_list_and_search(client) -> None:
    created = client.post(
        "/seeds",
        json={
            "name": "Lettuce",
            "variety": "Butterhead",
            "category": "leafy_green",
            "quantity": 9,
            "minimum_quantity": 3,
            "unit": "packet",
        },
    )
    assert created.status_code == 201
    seed_id = created.json()["id"]
    listed = client.get("/seeds")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    fetched = client.get(f"/seeds/{seed_id}")
    assert fetched.json()["variety"] == "Butterhead"
    search = client.get("/seeds/search", params={"q": "lett"})
    assert len(search.json()) == 1
    donate = client.post(f"/seeds/{seed_id}/donate", json={"quantity": 2})
    assert donate.json()["quantity"] == 11
