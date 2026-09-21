"""SQLAlchemy ORM models for GardenShare."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base
from app.utils.dates import utc_now


class Member(Base):
    """A community member who can borrow seeds and tend garden plots."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    borrow_requests: Mapped[list[BorrowRequest]] = relationship(back_populates="member")
    garden_plots: Mapped[list[GardenPlot]] = relationship(back_populates="member")


class Seed(Base):
    """A seed variety held in the community inventory."""

    __tablename__ = "seeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    variety: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minimum_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="packet")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    borrow_requests: Mapped[list[BorrowRequest]] = relationship(back_populates="seed")
    planting_plans: Mapped[list[PlantingPlan]] = relationship(back_populates="seed")


class BorrowRequest(Base):
    """A member request to borrow a quantity of a seed."""

    __tablename__ = "borrow_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    seed_id: Mapped[int] = mapped_column(ForeignKey("seeds.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    member: Mapped[Member] = relationship(back_populates="borrow_requests")
    seed: Mapped[Seed] = relationship(back_populates="borrow_requests")


class GardenPlot(Base):
    """A physical garden bed assigned to a member."""

    __tablename__ = "garden_plots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    size_sq_meters: Mapped[float] = mapped_column(nullable=False)

    member: Mapped[Member] = relationship(back_populates="garden_plots")
    planting_plans: Mapped[list[PlantingPlan]] = relationship(back_populates="garden_plot")


class PlantingPlan(Base):
    """A scheduled planting of a seed variety in a garden plot."""

    __tablename__ = "planting_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    garden_plot_id: Mapped[int] = mapped_column(ForeignKey("garden_plots.id"), nullable=False)
    seed_id: Mapped[int] = mapped_column(ForeignKey("seeds.id"), nullable=False)
    planting_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expected_harvest_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")

    garden_plot: Mapped[GardenPlot] = relationship(back_populates="planting_plans")
    seed: Mapped[Seed] = relationship(back_populates="planting_plans")
