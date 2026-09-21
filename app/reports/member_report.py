"""Member activity, tenure, and borrower reports.

Member reports describe people and their borrow history. They are not
substitutes for planting schedules or inventory restock lists.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.borrowing.policies import BorrowStatus, is_request_overdue
from app.database.models import BorrowRequest, GardenPlot, Member
from app.members.service import build_membership_card_code, list_members, membership_anniversary_month
from app.utils.dates import utc_now


def generate_member_activity_report(db: Session) -> dict:
    """Summarize each member's borrow and garden-plot activity."""

    members = list_members(db)
    rows = []
    for member in members:
        requests = list(
            db.scalars(select(BorrowRequest).where(BorrowRequest.member_id == member.id))
        )
        plots = list(db.scalars(select(GardenPlot).where(GardenPlot.member_id == member.id)))
        approved = [item for item in requests if item.status == BorrowStatus.APPROVED.value]
        overdue = [item for item in approved if is_request_overdue(item)]
        rows.append(
            {
                "member_id": member.id,
                "name": member.name,
                "email": member.email,
                "active": member.active,
                "joined_at": member.joined_at.isoformat(sep=" "),
                "borrow_request_count": len(requests),
                "active_borrow_count": len(approved),
                "overdue_borrow_count": len(overdue),
                "garden_plot_count": len(plots),
            }
        )
    return {
        "generated_at": utc_now().isoformat(sep=" "),
        "member_count": len(rows),
        "members": rows,
    }


def generate_active_borrowers_report(db: Session) -> dict:
    """List members who currently hold approved, unreturned seeds."""

    activity = generate_member_activity_report(db)
    borrowers = [row for row in activity["members"] if row["active_borrow_count"] > 0]
    return {
        "generated_at": activity["generated_at"],
        "active_borrower_count": len(borrowers),
        "borrowers": borrowers,
    }


def generate_overdue_borrow_report(db: Session) -> dict:
    """List members with overdue approved borrow requests."""

    activity = generate_member_activity_report(db)
    overdue_members = [row for row in activity["members"] if row["overdue_borrow_count"] > 0]
    return {
        "generated_at": activity["generated_at"],
        "overdue_member_count": len(overdue_members),
        "members": overdue_members,
    }


def generate_member_tenure_report(db: Session) -> dict:
    """Directory-style tenure summary used for anniversary postcards.

    This report is about membership duration, not seed quantities.
    """

    members = list_members(db)
    rows = []
    for member in members:
        rows.append(
            {
                "member_id": member.id,
                "name": member.name,
                "membership_card_code": build_membership_card_code(member),
                "anniversary_month": membership_anniversary_month(member.joined_at),
                "joined_at": member.joined_at.isoformat(sep=" "),
            }
        )
    return {
        "generated_at": utc_now().isoformat(sep=" "),
        "member_count": len(rows),
        "members": rows,
    }
