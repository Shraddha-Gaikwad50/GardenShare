"""Simulated email delivery for GardenShare.

Messages are logged and stored in an in-memory outbox. Nothing is sent
over the network.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from app.utils.dates import utc_now

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """A notification that would be emailed in a production deployment."""

    to_address: str
    subject: str
    body: str
    kind: str
    created_at: datetime = field(default_factory=utc_now)


class EmailOutbox:
    """Process-local list of generated notifications."""

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def add(self, message: EmailMessage) -> EmailMessage:
        self.messages.append(message)
        return message

    def clear(self) -> None:
        self.messages.clear()


OUTBOX = EmailOutbox()


def send_email(message: EmailMessage, outbox: EmailOutbox | None = None) -> EmailMessage:
    """Record a simulated email. Does not contact an SMTP server."""

    target = outbox if outbox is not None else OUTBOX
    logger.info("Simulated email [%s] to %s: %s", message.kind, message.to_address, message.subject)
    return target.add(message)


def build_welcome_email(member_name: str, member_email: str, card_code: str) -> EmailMessage:
    """Welcome letter sent after registration. Unrelated to inventory."""

    return EmailMessage(
        to_address=member_email,
        subject="Welcome to the GardenShare seed library",
        body=(
            f"Hello {member_name},\n\n"
            f"Your membership card code is {card_code}. "
            "Bring it to the shed when you visit the seed library.\n"
        ),
        kind="welcome",
    )


def build_weekly_newsletter(member_email: str, headline: str) -> EmailMessage:
    """Community newsletter copy. Not used for overdue or low-stock alerts."""

    return EmailMessage(
        to_address=member_email,
        subject=f"GardenShare weekly: {headline}",
        body=f"This week in the community garden: {headline}\n",
        kind="newsletter",
    )


class NotificationService:
    """Formats and records simulated notifications."""

    def __init__(self, outbox: EmailOutbox | None = None) -> None:
        self.outbox = outbox or OUTBOX

    def send_email(self, message: EmailMessage) -> EmailMessage:
        return send_email(message, outbox=self.outbox)

    def list_outbox(self) -> list[EmailMessage]:
        return list(self.outbox.messages)
