"""Shared pytest fixtures using an in-memory SQLite database."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.database.models import BorrowRequest, GardenPlot, Member, PlantingPlan, Seed  # noqa: F401
from app.main import app
from app.members.service import create_member
from app.seeds.catalog import add_seed


@pytest.fixture()
def engine():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def _fk(dbapi_connection, _record) -> None:  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture()
def db(engine) -> Session:
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine, db: Session) -> TestClient:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def member(db: Session) -> Member:
    return create_member(db, "Alice Green", "alice@example.com")


@pytest.fixture()
def tomato(db: Session) -> Seed:
    return add_seed(
        db,
        name="Tomato",
        variety="Cherry",
        category="vegetable",
        quantity=10,
        minimum_quantity=4,
        unit="packet",
    )
