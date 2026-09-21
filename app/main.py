"""GardenShare FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app import __version__
from app.borrowing.router import router as borrowing_router
from app.database.database import init_database
from app.gardens.router import router as gardens_router
from app.members.router import router as members_router
from app.notifications.router import router as notifications_router
from app.seeds.router import router as seeds_router
from app.utils.validation import GardenShareError
from app.web import page_shell, prefers_html, render_status_page

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("gardenshare")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create local SQLite tables on startup."""

    init_database()
    logger.info("GardenShare database ready")
    yield


app = FastAPI(
    title="GardenShare",
    description="Community seed-sharing and garden inventory management.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/swagger",
    redoc_url=None,
)

app.include_router(members_router)
app.include_router(seeds_router)
app.include_router(borrowing_router)
app.include_router(gardens_router)
app.include_router(notifications_router)


@app.exception_handler(GardenShareError)
async def gardenshare_error_handler(_request: Request, exc: GardenShareError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    """Browser landing page with links to docs and the main API routes."""

    cards = "".join(
        f'<li><a href="{href}">{label}</a></li>'
        for href, label in [
            ("/docs", "API docs"),
            ("/members", "Members"),
            ("/seeds", "Seeds"),
            ("/borrow-requests", "Borrow requests"),
            ("/gardens/plots", "Garden plots"),
            ("/health", "Health check"),
            ("/borrow-requests/overdue", "Overdue borrows"),
            ("/gardens/planting-plans/upcoming", "Upcoming plantings"),
        ]
    )
    body = f"""
    <p class="lead">Community seed-sharing and garden inventory management.</p>
    <p class="count">Service is running.</p>
    <ul class="home-links">{cards}</ul>
    <style>
      .home-links {{ list-style: none; padding: 0; margin: 1rem 0 0; }}
      .home-links li {{ margin: 0 0 0.65rem; }}
      .home-links a {{
        display: block;
        background: #fff;
        border: 1px solid #d8e3d3;
        border-radius: 10px;
        padding: 0.85rem 1rem;
        color: #2d6a4f;
        text-decoration: none;
        box-shadow: 0 6px 16px rgba(27, 67, 50, 0.06);
      }}
      .home-links a:hover {{ background: #edf5e8; }}
    </style>
    """
    return page_shell("Welcome", body)


@app.get("/docs", include_in_schema=False)
def api_docs_page() -> HTMLResponse:
    """Pretty wrapper around the interactive OpenAPI explorer."""

    body = """
    <p class="lead">Try the JSON API from this page. Use <code>GET</code> on members, seeds, borrows, and plots.</p>
    <div class="table-wrap" style="height: 78vh;">
      <iframe src="/swagger" title="GardenShare API docs" style="width:100%;height:78vh;border:0;"></iframe>
    </div>
    """
    return HTMLResponse(page_shell("API docs", body))


@app.get("/health")
def health(request: Request):
    """Liveness probe for local runs."""

    payload = {"status": "ok", "service": "gardenshare"}
    if prefers_html(request):
        return HTMLResponse(
            render_status_page(
                "Health",
                "The GardenShare service is up.",
                [("Status", payload["status"]), ("Service", payload["service"])],
            )
        )
    return payload
