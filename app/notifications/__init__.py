"""Simulated community notifications. No real email is sent."""

from app.notifications.email import EmailMessage, NotificationService, send_email
from app.notifications.reminders import (
    build_low_inventory_alert,
    build_overdue_reminder,
    build_planting_reminder,
)

__all__ = [
    "EmailMessage",
    "NotificationService",
    "build_low_inventory_alert",
    "build_overdue_reminder",
    "build_planting_reminder",
    "send_email",
]
