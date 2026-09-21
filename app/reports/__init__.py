"""Structured report generators. No HTML frontend is included."""

from app.reports.inventory_report import generate_inventory_report, generate_low_stock_report
from app.reports.member_report import generate_member_activity_report

__all__ = [
    "generate_inventory_report",
    "generate_low_stock_report",
    "generate_member_activity_report",
]
