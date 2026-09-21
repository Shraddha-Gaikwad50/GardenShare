"""Populate a local GardenShare database with demo members, seeds, and activity.

Safe to re-run: pass ``--reset`` to clear existing rows first.

    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --reset
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from app.borrowing.service import approve_borrow_request, create_borrow_request  # noqa: E402
from app.database.database import SessionLocal, init_database  # noqa: E402
from app.database.models import BorrowRequest, GardenPlot, Member, PlantingPlan, Seed  # noqa: E402
from app.gardens.planner import create_garden_plot, create_planting_plan  # noqa: E402
from app.members.service import create_member  # noqa: E402
from app.seeds.catalog import add_seed  # noqa: E402
from app.seeds.inventory import decrease_inventory  # noqa: E402
from app.utils.dates import utc_now  # noqa: E402


def reset_database(db) -> None:
    db.execute(text("DELETE FROM planting_plans"))
    db.execute(text("DELETE FROM garden_plots"))
    db.execute(text("DELETE FROM borrow_requests"))
    db.execute(text("DELETE FROM seeds"))
    db.execute(text("DELETE FROM members"))
    db.commit()


def seed(db) -> None:
    alice = create_member(db, "Alice Green", "alice.green@example.com")
    ravi = create_member(db, "Ravi Kumar", "ravi.kumar@example.com")
    maya = create_member(db, "Maya Shah", "maya.shah@example.com")

    tomato = add_seed(
        db,
        name="Tomato",
        variety="Cherry",
        category="vegetable",
        quantity=12,
        minimum_quantity=4,
    )
    carrot = add_seed(
        db,
        name="Carrot",
        variety="Nantes",
        category="vegetable",
        quantity=9,
        minimum_quantity=3,
    )
    basil = add_seed(
        db,
        name="Basil",
        variety="Genovese",
        category="herb",
        quantity=6,
        minimum_quantity=2,
    )
    lettuce = add_seed(
        db,
        name="Lettuce",
        variety="Butterhead",
        category="leafy_green",
        quantity=8,
        minimum_quantity=3,
    )
    add_seed(
        db,
        name="Marigold",
        variety="Orange",
        category="flower",
        quantity=10,
        minimum_quantity=2,
    )

    alice_borrow = create_borrow_request(db, member_id=alice.id, seed_id=tomato.id, quantity=3)
    approve_borrow_request(db, alice_borrow.id)

    ravi_borrow = create_borrow_request(db, member_id=ravi.id, seed_id=basil.id, quantity=2)
    approve_borrow_request(db, ravi_borrow.id)
    ravi_borrow.due_date = utc_now() - timedelta(days=3)
    db.commit()

    maya_plot = create_garden_plot(
        db,
        member_id=maya.id,
        name="Shady Lettuce Bed",
        location="East path, community garden",
        size_sq_meters=3.5,
    )
    create_planting_plan(
        db,
        garden_plot_id=maya_plot.id,
        seed_id=lettuce.id,
        planting_date=utc_now() + timedelta(days=1),
    )

    alice_plot = create_garden_plot(
        db,
        member_id=alice.id,
        name="Tomato Terrace",
        location="South wall",
        size_sq_meters=5.0,
    )
    create_planting_plan(
        db,
        garden_plot_id=alice_plot.id,
        seed_id=tomato.id,
        planting_date=utc_now() + timedelta(days=7),
    )

    # Leave carrot slightly above minimum so a later donation/borrow demo is obvious.
    decrease_inventory(db, carrot.id, 1)

    print("Demo data loaded:")
    print(f"  members: {db.query(Member).count()}")
    print(f"  seeds: {db.query(Seed).count()}")
    print(f"  borrow requests: {db.query(BorrowRequest).count()}")
    print(f"  garden plots: {db.query(GardenPlot).count()}")
    print(f"  planting plans: {db.query(PlantingPlan).count()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load GardenShare demo data")
    parser.add_argument("--reset", action="store_true", help="Delete existing rows before seeding")
    args = parser.parse_args()

    init_database()
    db = SessionLocal()
    try:
        existing = db.query(Member).count()
        if existing and not args.reset:
            print("Database already has members. Re-run with --reset to reload demo data.")
            return
        if args.reset:
            reset_database(db)
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
