"""HTTP routes for seed borrowing requests."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.borrowing.service import BorrowingService
from app.database.database import get_db
from app.web import dump_models, html_or_json

router = APIRouter(prefix="/borrow-requests", tags=["borrowing"])


class BorrowRequestCreate(BaseModel):
    member_id: int = Field(..., ge=1)
    seed_id: int = Field(..., ge=1)
    quantity: int = Field(..., gt=0)


class BorrowRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    seed_id: int
    quantity: int
    requested_at: datetime
    due_date: datetime
    returned_at: datetime | None
    status: str


@router.post("", response_model=BorrowRequestRead, status_code=status.HTTP_201_CREATED)
def create_request(payload: BorrowRequestCreate, db: Session = Depends(get_db)) -> BorrowRequestRead:
    """Submit a pending borrow request and reserve inventory."""

    request = BorrowingService(db).create_borrow_request(
        member_id=payload.member_id,
        seed_id=payload.seed_id,
        quantity=payload.quantity,
    )
    return BorrowRequestRead.model_validate(request)


def _borrow_rows(requests) -> list[dict]:
    return [
        {
            "id": item.id,
            "member": item.member.name if item.member else item.member_id,
            "seed": f"{item.seed.name} / {item.seed.variety}" if item.seed else item.seed_id,
            "quantity": item.quantity,
            "due_date": item.due_date,
            "status": item.status,
        }
        for item in requests
    ]


@router.get("", response_model=None)
def list_active_requests(request: Request, db: Session = Depends(get_db)) -> HTMLResponse | JSONResponse:
    """List approved, not-yet-returned borrow requests."""

    requests = BorrowingService(db).get_active_borrow_requests()
    payload = dump_models([BorrowRequestRead.model_validate(item) for item in requests])
    return html_or_json(
        request,
        payload,
        title="Borrow requests",
        subtitle="Approved requests that have not been returned yet.",
        columns=[
            ("id", "ID"),
            ("member", "Member"),
            ("seed", "Seed"),
            ("quantity", "Quantity"),
            ("due_date", "Due"),
            ("status", "Status"),
        ],
        rows=_borrow_rows(requests),
    )


@router.get("/overdue", response_model=None)
def list_overdue_requests(request: Request, db: Session = Depends(get_db)) -> HTMLResponse | JSONResponse:
    """List approved borrow requests that are past their due date."""

    requests = BorrowingService(db).get_overdue_requests()
    payload = dump_models([BorrowRequestRead.model_validate(item) for item in requests])
    return html_or_json(
        request,
        payload,
        title="Overdue borrows",
        subtitle="Approved requests whose due date has already passed.",
        columns=[
            ("id", "ID"),
            ("member", "Member"),
            ("seed", "Seed"),
            ("quantity", "Quantity"),
            ("due_date", "Due"),
            ("status", "Status"),
        ],
        rows=_borrow_rows(requests),
    )


@router.post("/{request_id}/approve", response_model=BorrowRequestRead)
def approve_request(request_id: int, db: Session = Depends(get_db)) -> BorrowRequestRead:
    """Approve a pending request and decrease seed inventory."""

    request = BorrowingService(db).approve_borrow_request(request_id)
    return BorrowRequestRead.model_validate(request)


@router.post("/{request_id}/reject", response_model=BorrowRequestRead)
def reject_request(request_id: int, db: Session = Depends(get_db)) -> BorrowRequestRead:
    """Reject a pending request without changing on-hand inventory."""

    request = BorrowingService(db).reject_borrow_request(request_id)
    return BorrowRequestRead.model_validate(request)


@router.post("/{request_id}/return", response_model=BorrowRequestRead)
def return_request(request_id: int, db: Session = Depends(get_db)) -> BorrowRequestRead:
    """Return borrowed seeds and restore inventory."""

    request = BorrowingService(db).return_seed(request_id)
    return BorrowRequestRead.model_validate(request)
