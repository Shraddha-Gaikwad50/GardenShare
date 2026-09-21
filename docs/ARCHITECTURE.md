# GardenShare Architecture

GardenShare is a local community seed-sharing and garden inventory application.
It runs as a single FastAPI process with SQLite. There are no cloud services,
message queues, or external identity providers.

## Request flow

```
Customer / HTTP client
        ↓
FastAPI routers  (app/*/router.py)
        ↓
Services / domain logic
        (members, catalog, inventory, borrowing, planner, notifications, reports)
        ↓
SQLAlchemy models and session
        ↓
SQLite  (data/gardenshare.db)
```

Routers accept and return Pydantic schemas. They do not contain inventory
rules, due-date policy, or crop-duration math. Those live in service modules
so the same logic can be used from tests, scripts, and reports.

## Layers

### API layer

`app/main.py` builds the FastAPI app, registers routers, exposes `GET /health`,
and maps `GardenShareError` to HTTP status codes.

Routers:

- `app/members/router.py` — registration and deactivation
- `app/seeds/router.py` — catalog search and donations
- `app/borrowing/router.py` — borrow, approve, reject, return
- `app/gardens/router.py` — plots and planting plans
- `app/notifications/router.py` — simulated reminders (no real email)

### Service / business logic

- **Members** (`app/members/service.py`) — create, list, deactivate, email checks
- **Catalog** (`app/seeds/catalog.py`) — add and search seed varieties
- **Inventory** (`app/seeds/inventory.py`) — on-hand quantity, reserve/release, low-stock threshold
- **Borrowing** (`app/borrowing/service.py` + `policies.py`) — request lifecycle and rules
- **Gardens** (`app/gardens/planner.py`) — plots, crop duration, harvest dates
- **Notifications** (`app/notifications/email.py` + `reminders.py`) — message text and an in-memory outbox
- **Reports** (`app/reports/`) — dictionaries describing inventory and member activity

### Database layer

- `app/database/database.py` — engine, session, `get_db`, table creation
- `app/database/models.py` — SQLAlchemy models: Member, Seed, BorrowRequest, GardenPlot, PlantingPlan

## Major modules

| Module | Responsibility |
| --- | --- |
| `members` | Community identity: names, emails, active flag, membership card codes |
| `seeds.catalog` | What varieties exist and how to search them |
| `seeds.inventory` | How many packets are on the shelf |
| `borrowing` | Who may take packets, due dates, returns |
| `gardens` | Physical plots and planting calendars |
| `notifications` | Wording of reminders; simulated delivery |
| `reports` | Read-only summaries for coordinators |
| `utils.dates` | UTC timestamps, due dates, overdue checks |
| `utils.validation` | Quantity, email, and string checks |

## Configuration

`app/config/settings.py` holds local paths and defaults such as the 14-day
borrow window. Settings are in-process constants, not environment secrets.

## What this codebase is not

GardenShare does not implement authentication servers, payment processing,
or a web frontend. Reports are Python dictionaries (and optional JSON via
existing routers for reminders), not dashboards.
