"""Garden plot and planting plan tests."""

from __future__ import annotations

from datetime import timedelta

from app.gardens.planner import (
    calculate_expected_harvest,
    create_garden_plot,
    create_planting_plan,
    crop_duration_days,
    get_upcoming_plantings,
    list_garden_plots,
)
from app.utils.dates import utc_now


def test_create_garden_plot(db, member) -> None:
    plot = create_garden_plot(
        db,
        member_id=member.id,
        name="Bed A",
        location="North fence",
        size_sq_meters=4.5,
    )
    assert plot.member_id == member.id
    assert len(list_garden_plots(db)) == 1


def test_crop_duration_rules() -> None:
    assert crop_duration_days("Tomato") == 80
    assert crop_duration_days("Carrot") == 70
    assert crop_duration_days("Basil") == 45
    assert crop_duration_days("Lettuce") == 40


def test_create_planting_plan_sets_harvest_date(db, member, tomato) -> None:
    plot = create_garden_plot(
        db,
        member_id=member.id,
        name="Bed A",
        location="North fence",
        size_sq_meters=4.5,
    )
    planting = utc_now() + timedelta(days=2)
    plan = create_planting_plan(
        db,
        garden_plot_id=plot.id,
        seed_id=tomato.id,
        planting_date=planting,
    )
    expected = calculate_expected_harvest("Tomato", planting)
    assert plan.expected_harvest_date == expected
    upcoming = get_upcoming_plantings(db)
    assert len(upcoming) == 1


def test_garden_api(client) -> None:
    member = client.post("/members", json={"name": "Maya Shah", "email": "maya@example.com"}).json()
    seed = client.post(
        "/seeds",
        json={
            "name": "Lettuce",
            "variety": "Butterhead",
            "category": "leafy_green",
            "quantity": 8,
            "minimum_quantity": 2,
        },
    ).json()
    plot = client.post(
        "/gardens/plots",
        json={
            "member_id": member["id"],
            "name": "Shady Bed",
            "location": "East path",
            "size_sq_meters": 3.0,
        },
    )
    assert plot.status_code == 201
    planting_date = (utc_now() + timedelta(days=1)).isoformat()
    plan = client.post(
        "/gardens/planting-plans",
        json={
            "garden_plot_id": plot.json()["id"],
            "seed_id": seed["id"],
            "planting_date": planting_date,
        },
    )
    assert plan.status_code == 201
    assert plan.json()["status"] == "scheduled"
    upcoming = client.get("/gardens/planting-plans/upcoming")
    assert upcoming.status_code == 200
    assert len(upcoming.json()) == 1
