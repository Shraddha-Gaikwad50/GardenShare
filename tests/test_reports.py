"""Inventory and member report tests."""

from __future__ import annotations

from app.borrowing.service import approve_borrow_request, create_borrow_request
from app.reports.inventory_report import generate_inventory_report, generate_low_stock_report
from app.reports.member_report import generate_member_activity_report
from app.seeds.catalog import add_seed


def test_inventory_report_summarizes_catalog(db, tomato) -> None:
    add_seed(db, name="Basil", variety="Genovese", category="herb", quantity=2, minimum_quantity=5)
    report = generate_inventory_report(db)
    assert report["seed_count"] == 2
    names = {item["name"] for item in report["items"]}
    assert names == {"Tomato", "Basil"}


def test_low_stock_report_includes_strictly_below_minimum(db) -> None:
    add_seed(db, name="Basil", variety="Genovese", category="herb", quantity=2, minimum_quantity=5)
    add_seed(db, name="Marigold", variety="Orange", category="flower", quantity=9, minimum_quantity=3)
    report = generate_low_stock_report(db)
    assert report["low_stock_count"] == 1
    assert report["items"][0]["name"] == "Basil"


def test_member_activity_report_counts_borrows(db, member, tomato) -> None:
    request = create_borrow_request(db, member_id=member.id, seed_id=tomato.id, quantity=2)
    approve_borrow_request(db, request.id)
    report = generate_member_activity_report(db)
    assert report["member_count"] == 1
    row = report["members"][0]
    assert row["borrow_request_count"] == 1
    assert row["active_borrow_count"] == 1
