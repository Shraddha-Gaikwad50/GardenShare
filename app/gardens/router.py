"""HTTP routes for garden plots and planting plans."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.web import dump_models, html_or_json
from app.gardens.models import (
    CompanionPlantingHint,
    GardenPlotAssign,
    GardenPlotCreate,
    GardenPlotRead,
    PlantingPlanCreate,
    PlantingPlanRead,
)
from app.gardens.planner import GardenPlanner, companion_planting_for, get_garden_plot
from app.seeds.catalog import get_seed

router = APIRouter(prefix="/gardens", tags=["gardens"])


@router.post("/plots", response_model=GardenPlotRead, status_code=status.HTTP_201_CREATED)
def create_plot(payload: GardenPlotCreate, db: Session = Depends(get_db)) -> GardenPlotRead:
    """Create a garden plot assigned to a member."""

    plot = GardenPlanner(db).create_garden_plot(
        member_id=payload.member_id,
        name=payload.name,
        location=payload.location,
        size_sq_meters=payload.size_sq_meters,
    )
    return GardenPlotRead.model_validate(plot)


@router.get("/plots", response_model=None)
def list_plots(
    request: Request,
    member_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse | JSONResponse:
    """List garden plots."""

    plots = GardenPlanner(db).list_garden_plots(member_id=member_id)
    payload = dump_models([GardenPlotRead.model_validate(plot) for plot in plots])
    rows = [
        {
            "id": plot.id,
            "name": plot.name,
            "location": plot.location,
            "size_sq_meters": plot.size_sq_meters,
            "member": plot.member.name if plot.member else plot.member_id,
        }
        for plot in plots
    ]
    return html_or_json(
        request,
        payload,
        title="Garden plots",
        subtitle="Beds assigned to community members.",
        columns=[
            ("id", "ID"),
            ("name", "Plot"),
            ("location", "Location"),
            ("size_sq_meters", "Size (m²)"),
            ("member", "Member"),
        ],
        rows=rows,
    )


@router.post("/plots/{plot_id}/assign", response_model=GardenPlotRead)
def assign_plot(plot_id: int, payload: GardenPlotAssign, db: Session = Depends(get_db)) -> GardenPlotRead:
    """Reassign a plot to another member."""

    plot = GardenPlanner(db).assign_plot_member(plot_id, payload.member_id)
    return GardenPlotRead.model_validate(plot)


@router.post("/planting-plans", response_model=PlantingPlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlantingPlanCreate, db: Session = Depends(get_db)) -> PlantingPlanRead:
    """Schedule a planting and calculate the expected harvest date."""

    plan = GardenPlanner(db).create_planting_plan(
        garden_plot_id=payload.garden_plot_id,
        seed_id=payload.seed_id,
        planting_date=payload.planting_date,
        status=payload.status,
    )
    return PlantingPlanRead.model_validate(plan)


@router.get("/planting-plans/upcoming", response_model=None)
def upcoming_plantings(request: Request, db: Session = Depends(get_db)) -> HTMLResponse | JSONResponse:
    """List scheduled plantings that have not yet occurred."""

    plans = GardenPlanner(db).get_upcoming_plantings()
    payload = dump_models([PlantingPlanRead.model_validate(plan) for plan in plans])
    rows = [
        {
            "id": plan.id,
            "plot": plan.garden_plot.name if plan.garden_plot else plan.garden_plot_id,
            "seed": f"{plan.seed.name} / {plan.seed.variety}" if plan.seed else plan.seed_id,
            "planting_date": plan.planting_date,
            "expected_harvest_date": plan.expected_harvest_date,
            "status": plan.status,
        }
        for plan in plans
    ]
    return html_or_json(
        request,
        payload,
        title="Upcoming plantings",
        subtitle="Scheduled sowing dates that have not happened yet.",
        columns=[
            ("id", "ID"),
            ("plot", "Plot"),
            ("seed", "Seed"),
            ("planting_date", "Planting"),
            ("expected_harvest_date", "Harvest"),
            ("status", "Status"),
        ],
        rows=rows,
    )


@router.get("/plots/{plot_id}/companions", response_model=CompanionPlantingHint)
def plot_companion_hint(plot_id: int, seed_id: int, db: Session = Depends(get_db)) -> CompanionPlantingHint:
    """Return companion-planting guidance for signage on a plot."""

    get_garden_plot(db, plot_id)
    seed = get_seed(db, seed_id)
    hint = companion_planting_for(seed.name)
    return CompanionPlantingHint(crop=seed.name.lower(), companions=hint["companions"], avoid=hint["avoid"])
