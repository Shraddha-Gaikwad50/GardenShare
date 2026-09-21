"""Notification formatting and simulated delivery tests."""

from __future__ import annotations

from app.database.models import BorrowRequest, Member, Seed
from app.gardens.planner import create_garden_plot, create_planting_plan
from app.notifications.email import EmailOutbox, send_email
from app.notifications.reminders import (
    build_low_inventory_alert,
    build_overdue_reminder,
    build_planting_reminder,
)
from app.seeds.catalog import add_seed
from app.utils.dates import add_days, utc_now


def test_send_email_records_outbox_message() -> None:
    outbox = EmailOutbox()
    member = Member(id=1, name="Alice Green", email="alice@example.com")
    seed = Seed(id=1, name="Tomato", variety="Cherry", category="vegetable", quantity=1, minimum_quantity=4, unit="packet")
    request = BorrowRequest(
        id=1,
        member_id=1,
        seed_id=1,
        quantity=2,
        requested_at=utc_now(),
        due_date=add_days(utc_now(), -3),
        status="approved",
    )
    built = build_overdue_reminder(member, request, seed)
    sent = send_email(built, outbox=outbox)
    assert sent.kind == "overdue_borrow"
    assert "overdue" in sent.subject.lower()
    assert len(outbox.messages) == 1


def test_low_inventory_alert_when_below_minimum(db) -> None:
    seed = add_seed(
        db,
        name="Tomato",
        variety="Cherry",
        category="vegetable",
        quantity=2,
        minimum_quantity=5,
    )
    alert = build_low_inventory_alert(seed)
    assert alert is not None
    assert "running low" in alert.subject.lower()


def test_low_inventory_alert_not_sent_when_comfortably_above_minimum(db, tomato) -> None:
    assert build_low_inventory_alert(tomato) is None


def test_planting_reminder_copy(db, member, tomato) -> None:
    plot = create_garden_plot(
        db,
        member_id=member.id,
        name="Bed A",
        location="North fence",
        size_sq_meters=2.0,
    )
    plan = create_planting_plan(
        db,
        garden_plot_id=plot.id,
        seed_id=tomato.id,
        planting_date=add_days(utc_now(), 1),
    )
    reminder = build_planting_reminder(member, plan, tomato)
    assert "lettuce" not in reminder.subject.lower()
    assert "planting date" in reminder.subject.lower()


def test_notification_dispatch_api_for_low_stock(client) -> None:
    client.post(
        "/seeds",
        json={
            "name": "Carrot",
            "variety": "Nantes",
            "category": "vegetable",
            "quantity": 1,
            "minimum_quantity": 5,
        },
    )
    response = client.post("/notifications/low-inventory-alerts")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "running low" in response.json()[0]["subject"].lower()
