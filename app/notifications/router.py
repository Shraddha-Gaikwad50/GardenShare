"""HTTP routes for simulated notifications and reminder dispatch."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.notifications.email import NotificationService
from app.notifications.reminders import (
    collect_low_inventory_alerts,
    collect_overdue_reminders,
    collect_planting_reminders,
    dispatch_all_reminders,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationRead(BaseModel):
    to_address: str
    subject: str
    body: str
    kind: str
    created_at: datetime


@router.get("/outbox", response_model=list[NotificationRead])
def list_outbox() -> list[NotificationRead]:
    """List simulated emails generated in this process."""

    messages = NotificationService().list_outbox()
    return [
        NotificationRead(
            to_address=item.to_address,
            subject=item.subject,
            body=item.body,
            kind=item.kind,
            created_at=item.created_at,
        )
        for item in messages
    ]


@router.post("/overdue-reminders", response_model=list[NotificationRead])
def send_overdue_reminders(db: Session = Depends(get_db)) -> list[NotificationRead]:
    """Generate overdue borrow reminders from current requests."""

    service = NotificationService()
    sent = [service.send_email(message) for message in collect_overdue_reminders(db)]
    return [_to_read(item) for item in sent]


@router.post("/low-inventory-alerts", response_model=list[NotificationRead])
def send_low_inventory_alerts(db: Session = Depends(get_db)) -> list[NotificationRead]:
    """Generate low-stock alerts from current catalog quantities."""

    service = NotificationService()
    sent = [service.send_email(message) for message in collect_low_inventory_alerts(db)]
    return [_to_read(item) for item in sent]


@router.post("/planting-reminders", response_model=list[NotificationRead])
def send_planting_reminders(db: Session = Depends(get_db)) -> list[NotificationRead]:
    """Generate planting-date reminders for upcoming plans."""

    service = NotificationService()
    sent = [service.send_email(message) for message in collect_planting_reminders(db)]
    return [_to_read(item) for item in sent]


@router.post("/dispatch", response_model=list[NotificationRead])
def dispatch_reminders(db: Session = Depends(get_db)) -> list[NotificationRead]:
    """Generate all reminder types and record them in the outbox."""

    sent = dispatch_all_reminders(db)
    return [_to_read(item) for item in sent]


def _to_read(item) -> NotificationRead:
    return NotificationRead(
        to_address=item.to_address,
        subject=item.subject,
        body=item.body,
        kind=item.kind,
        created_at=item.created_at,
    )
