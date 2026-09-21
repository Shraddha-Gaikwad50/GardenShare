"""Reminder and alert copy for overdue borrows, low stock, and plantings.

Formatting lives here. Inventory and borrowing modules decide *which*
records need attention; this module only builds message text.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.borrowing.service import get_overdue_requests
from app.config.settings import get_settings
from app.database.models import BorrowRequest, Member, PlantingPlan, Seed
from app.gardens.planner import get_upcoming_plantings
from app.notifications.email import EmailMessage, NotificationService
from app.seeds.catalog import list_available_seeds
from app.seeds.inventory import check_inventory_threshold, get_available_quantity
from app.utils.dates import days_until, utc_now


def build_overdue_reminder(member: Member, request: BorrowRequest, seed: Seed) -> EmailMessage:
    """Build a reminder that a seed borrowing request is overdue."""

    return EmailMessage(
        to_address=member.email,
        subject="Your seed borrowing request is overdue.",
        body=(
            f"Hello {member.name},\n\n"
            f"Your seed borrowing request is overdue. "
            f"Please return {request.quantity} {seed.unit}(s) of {seed.name} "
            f"({seed.variety}). The due date was {request.due_date.isoformat(sep=' ', timespec='minutes')}.\n"
        ),
        kind="overdue_borrow",
    )


def build_low_inventory_alert(seed: Seed, coordinator_email: str = "coordinator@gardenshare.local") -> EmailMessage | None:
    """Build a coordinator alert when a variety is running low.

    Uses the inventory threshold helper so catalog and reminders share a
    single definition of "low stock".
    """

    if not check_inventory_threshold(seed):
        return None
    available = get_available_quantity(seed)
    return EmailMessage(
        to_address=coordinator_email,
        subject=f"{seed.name} seeds are running low.",
        body=(
            f"{seed.name} ({seed.variety}) seeds are running low. "
            f"Available: {available} {seed.unit}(s). "
            f"Minimum quantity: {seed.minimum_quantity} {seed.unit}(s).\n"
        ),
        kind="low_inventory",
    )


def build_planting_reminder(member: Member, plan: PlantingPlan, seed: Seed) -> EmailMessage:
    """Build a reminder that a planting date is imminent."""

    remaining = days_until(plan.planting_date)
    when = "tomorrow" if remaining == 1 else ("today" if remaining == 0 else f"in {remaining} days")
    return EmailMessage(
        to_address=member.email,
        subject=f"Your {seed.name.lower()} planting date is {when}.",
        body=(
            f"Hello {member.name},\n\n"
            f"Your {seed.name.lower()} planting date is {when} "
            f"({plan.planting_date.date().isoformat()}). "
            f"Expected harvest: {plan.expected_harvest_date.date().isoformat()}.\n"
        ),
        kind="planting_reminder",
    )


def collect_overdue_reminders(db: Session) -> list[EmailMessage]:
    """Build overdue reminders for every past-due approved borrow."""

    messages: list[EmailMessage] = []
    for request in get_overdue_requests(db):
        messages.append(build_overdue_reminder(request.member, request, request.seed))
    return messages


def collect_low_inventory_alerts(db: Session) -> list[EmailMessage]:
    """Build low-stock alerts for catalog seeds under the minimum."""

    messages: list[EmailMessage] = []
    for seed in list_available_seeds(db):
        alert = build_low_inventory_alert(seed)
        if alert is not None:
            messages.append(alert)
    return messages


def collect_planting_reminders(db: Session) -> list[EmailMessage]:
    """Build reminders for plantings due within the configured lead time."""

    lead_days = get_settings().reminder_lead_days
    now = utc_now()
    messages: list[EmailMessage] = []
    for plan in get_upcoming_plantings(db, as_of=now):
        remaining = days_until(plan.planting_date, now)
        if 0 <= remaining <= lead_days:
            member = plan.garden_plot.member
            messages.append(build_planting_reminder(member, plan, plan.seed))
    return messages


def dispatch_all_reminders(db: Session, service: NotificationService | None = None) -> list[EmailMessage]:
    """Generate and record overdue, low-stock, and planting reminders."""

    notifier = service or NotificationService()
    generated = (
        collect_overdue_reminders(db)
        + collect_low_inventory_alerts(db)
        + collect_planting_reminders(db)
    )
    return [notifier.send_email(message) for message in generated]
