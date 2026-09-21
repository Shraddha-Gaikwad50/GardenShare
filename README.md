# GardenShare

GardenShare is a small community seed-sharing and garden inventory application.
Neighbors register, donate seed packets to a shared catalog, borrow varieties
for the season, return what they do not plant, and keep simple records of
garden plots and planting dates.

The app is designed to run on a laptop with Python 3.11+ and SQLite. It has
no cloud dependencies and no frontend: HTTP JSON plus a few report helpers.

## Architecture

```
HTTP client
    → FastAPI routers
        → services (members, catalog, inventory, borrowing, gardens, notifications, reports)
            → SQLAlchemy models
                → SQLite file data/gardenshare.db
```

Routers stay thin. Borrowing rules live in `app/borrowing/policies.py`.
Inventory math lives in `app/seeds/inventory.py`. Crop duration lives in
`app/gardens/planner.py`. Shared date helpers live in `app/utils/dates.py`.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/DOMAIN_MODEL.md](docs/DOMAIN_MODEL.md) for module and relationship
detail.

## Features

- Member registration, lookup, and deactivation
- Seed catalog with categories (vegetable, herb, flower, fruit, leafy_green)
- Inventory increase / decrease / reserve / release with validation
- Borrow requests: create, approve, reject, return, overdue listing
- Garden plots and planting plans with crop-duration harvest dates
- Simulated email reminders (logged, never sent over the network)
- Inventory and member activity reports as Python dictionaries

## Project structure

```
gardenshare/
├── app/
│   ├── main.py
│   ├── config/settings.py
│   ├── database/          # SQLite engine and ORM models
│   ├── members/           # registration and directory
│   ├── seeds/             # catalog + inventory
│   ├── borrowing/         # requests, policies, returns
│   ├── gardens/           # plots and planting planner
│   ├── notifications/     # simulated email and reminders
│   ├── reports/           # inventory and member summaries
│   └── utils/             # dates and validation
├── tests/
├── scripts/seed_demo_data.py
├── data/                  # SQLite file is created here at runtime
├── docs/
├── requirements.txt
└── README.md
```

## Installation

Python 3.11 or newer is required.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Running locally

From the repository root:

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health
- OpenAPI UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

Load sample members and seeds:

```bash
python scripts/seed_demo_data.py
```

Re-run with `--reset` to replace existing rows.

## Running tests

The default suite covers members, inventory, borrowing, gardens,
notifications, and reports:

```bash
pytest
```

Maintainer diagnostics live under `tests/demo_bugs/` and are excluded from
the default run (see `pytest.ini`). Execute them separately when needed:

```bash
pytest tests/demo_bugs/
```

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness |
| POST | `/members` | Register |
| GET | `/members` | List members |
| GET | `/members/{member_id}` | Get member |
| POST | `/members/{member_id}/deactivate` | Deactivate |
| GET | `/members/directory` | Membership directory |
| POST | `/seeds` | Add catalog variety |
| GET | `/seeds` | List / filter catalog |
| GET | `/seeds/search?q=` | Search by name |
| GET | `/seeds/{seed_id}` | Get seed |
| POST | `/seeds/{seed_id}/donate` | Increase inventory |
| POST | `/borrow-requests` | Request seeds |
| GET | `/borrow-requests` | Active approved requests |
| GET | `/borrow-requests/overdue` | Overdue requests |
| POST | `/borrow-requests/{id}/approve` | Approve and decrease stock |
| POST | `/borrow-requests/{id}/reject` | Reject without changing stock |
| POST | `/borrow-requests/{id}/return` | Return and restore stock |
| POST | `/gardens/plots` | Create plot |
| GET | `/gardens/plots` | List plots |
| POST | `/gardens/plots/{id}/assign` | Reassign plot |
| POST | `/gardens/planting-plans` | Schedule a planting |
| GET | `/gardens/planting-plans/upcoming` | Upcoming plantings |
| POST | `/notifications/overdue-reminders` | Simulated overdue emails |
| POST | `/notifications/low-inventory-alerts` | Simulated low-stock emails |
| POST | `/notifications/planting-reminders` | Simulated planting emails |
| GET | `/notifications/outbox` | Messages recorded in-process |

## Database

SQLite file: `data/gardenshare.db`

Tables: `members`, `seeds`, `borrow_requests`, `garden_plots`, `planting_plans`.
The file is created automatically on first startup. It is gitignored; keep
`data/.gitkeep` so the directory exists in a fresh clone.

## Example API requests

Health:

```bash
curl http://127.0.0.1:8000/health
```

Register a member and add tomato seeds:

```bash
curl -X POST http://127.0.0.1:8000/members ^
  -H "Content-Type: application/json" ^
  -d "{\"name\": \"Alice Green\", \"email\": \"alice@example.com\"}"

curl -X POST http://127.0.0.1:8000/seeds ^
  -H "Content-Type: application/json" ^
  -d "{\"name\": \"Tomato\", \"variety\": \"Cherry\", \"category\": \"vegetable\", \"quantity\": 12, \"minimum_quantity\": 4, \"unit\": \"packet\"}"
```

On macOS / Linux, use `\` line continuations and single quotes around JSON.

Search:

```bash
curl "http://127.0.0.1:8000/seeds/search?q=tomato"
```

## Example workflows

### Scenario 1 — Borrow tomato seeds

Alice registers (or already exists), tomato packets are in the catalog, then:

1. `POST /borrow-requests` with `member_id`, tomato `seed_id`, `quantity: 3`
2. `POST /borrow-requests/{id}/approve`

On-hand tomato inventory decreases by 3. The request is `approved` with a
due date 14 days out.

### Scenario 2 — Return borrowed seeds

When Alice brings packets back:

1. `POST /borrow-requests/{id}/return`

The request becomes `returned` and inventory increases. Returning twice is
rejected.

### Scenario 3 — Tomato inventory falls below minimum

If tomato `minimum_quantity` is 4 and available packets drop to 2
(donations reversed or several approved borrows):

1. `POST /notifications/low-inventory-alerts`

The simulated message subject is along the lines of
`Tomato seeds are running low.`

From Python:

```python
from app.reports.inventory_report import generate_low_stock_report
```

### Scenario 4 — Overdue borrowing request

An approved request whose due date is several days in the past appears in:

- `GET /borrow-requests/overdue`
- `POST /notifications/overdue-reminders`

Copy includes: `Your seed borrowing request is overdue.`

### Scenario 5 — Garden plot and lettuce planting

1. `POST /gardens/plots` for the member (name, location, size)
2. `POST /gardens/planting-plans` with the lettuce `seed_id` and a planting date

Lettuce harvest is estimated 40 days after planting. Upcoming work shows up
on `GET /gardens/planting-plans/upcoming`. A planting tomorrow can be turned
into a simulated reminder with `POST /notifications/planting-reminders`.

### Scenario 6 — Inventory report

There is no report router; coordinators generate summaries in Python:

```python
from app.database.database import SessionLocal
from app.reports.inventory_report import generate_inventory_report, generate_low_stock_report
from app.reports.member_report import generate_member_activity_report

db = SessionLocal()
print(generate_inventory_report(db))
print(generate_low_stock_report(db))
print(generate_member_activity_report(db))
db.close()
```

## Development notes

- Type hints and small service functions are preferred over logic in routers.
- Notifications never call SMTP; they append to an in-process outbox and log.
- Default borrow window is 14 days (`app/config/settings.py`).
- Crop durations are in `app/gardens/planner.py` (`CROP_DURATION_DAYS`).
- Interactive API docs are served by FastAPI at `/docs`.
- Additional maintainer docs live in `docs/`.
