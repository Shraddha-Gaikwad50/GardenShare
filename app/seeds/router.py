"""HTTP routes for the seed catalog and inventory donations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.seeds.catalog import SeedCatalog, format_seed_packet_label, recommended_planting_season
from app.seeds.inventory import InventoryManager, get_available_quantity
from app.seeds.models import InventoryAdjustment, SeedCreate, SeedPacketLabel, SeedRead
from app.web import dump_models, html_or_json

router = APIRouter(prefix="/seeds", tags=["seeds"])


@router.post("", response_model=SeedRead, status_code=status.HTTP_201_CREATED)
def create_seed(payload: SeedCreate, db: Session = Depends(get_db)) -> SeedRead:
    """Add a seed variety to the community catalog."""

    seed = SeedCatalog(db).add_seed(
        name=payload.name,
        variety=payload.variety,
        category=payload.category.value,
        quantity=payload.quantity,
        minimum_quantity=payload.minimum_quantity,
        unit=payload.unit,
    )
    return SeedRead.model_validate(seed)


@router.get("", response_model=None)
def list_seeds(
    request: Request,
    category: str | None = None,
    in_stock_only: bool = False,
    db: Session = Depends(get_db),
) -> HTMLResponse | JSONResponse:
    """List catalog seeds, optionally filtered by category."""

    catalog = SeedCatalog(db)
    if category:
        seeds = catalog.filter_by_category(category)
        if in_stock_only:
            seeds = [seed for seed in seeds if get_available_quantity(seed) > 0]
    else:
        seeds = catalog.list_available_seeds(in_stock_only=in_stock_only)
    payload = dump_models([SeedRead.model_validate(seed) for seed in seeds])
    rows = [
        {
            "id": seed.id,
            "name": seed.name,
            "variety": seed.variety,
            "category": seed.category,
            "quantity": seed.quantity,
            "minimum_quantity": seed.minimum_quantity,
            "unit": seed.unit,
        }
        for seed in seeds
    ]
    return html_or_json(
        request,
        payload,
        title="Seeds",
        subtitle="Varieties currently in the community catalog.",
        columns=[
            ("id", "ID"),
            ("name", "Name"),
            ("variety", "Variety"),
            ("category", "Category"),
            ("quantity", "On hand"),
            ("minimum_quantity", "Minimum"),
            ("unit", "Unit"),
        ],
        rows=rows,
    )


@router.get("/search", response_model=list[SeedRead])
def search_catalog(
    q: str | None = Query(default=None, description="Substring match against seed name"),
    variety: str | None = Query(default=None, description="Substring match against variety"),
    db: Session = Depends(get_db),
) -> list[SeedRead]:
    """Search seeds by name and/or variety."""

    catalog = SeedCatalog(db)
    if q:
        seeds = catalog.search_seeds(q)
    else:
        seeds = catalog.list_available_seeds()
    if variety:
        needle = variety.lower()
        seeds = [seed for seed in seeds if needle in seed.variety.lower()]
    return [SeedRead.model_validate(seed) for seed in seeds]


@router.get("/{seed_id}", response_model=SeedRead)
def get_catalog_seed(seed_id: int, db: Session = Depends(get_db)) -> SeedRead:
    """Fetch a single seed variety."""

    seed = SeedCatalog(db).get_seed(seed_id)
    return SeedRead.model_validate(seed)


@router.get("/{seed_id}/label", response_model=SeedPacketLabel)
def get_packet_label(seed_id: int, db: Session = Depends(get_db)) -> SeedPacketLabel:
    """Return a printable packet label. Not an inventory mutation."""

    seed = SeedCatalog(db).get_seed(seed_id)
    return SeedPacketLabel(
        seed_id=seed.id,
        title=format_seed_packet_label(seed),
        season_hint=recommended_planting_season(seed.name),
        category=seed.category,
    )


@router.post("/{seed_id}/donate", response_model=SeedRead)
def donate_seed_packets(
    seed_id: int,
    payload: InventoryAdjustment,
    db: Session = Depends(get_db),
) -> SeedRead:
    """Increase inventory when a member donates additional packets."""

    seed = InventoryManager(db).increase_inventory(seed_id, payload.quantity)
    return SeedRead.model_validate(seed)
