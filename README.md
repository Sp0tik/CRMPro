# CRMPro

![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688)
![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-4169E1)
![Docker Compose](https://img.shields.io/badge/Docker%20Compose-ready-2496ED)

**CRMPro** is a full-stack customer relationship management system: a FastAPI + SQLAlchemy 2.0
backend with PostgreSQL (or zero-setup SQLite for local development), JWT authentication with
roles, and a dependency-free HTML/CSS/JS single-page interface served directly by the API.

- Clients, deals pipeline, tasks, support tickets, team users and analytics in one app
- Role-based access (`admin` / `manager`), documented REST API with OpenAPI docs
- One-command launch with Docker Compose, seeded demo data included

## Features

- **Auth**: JWT (HS256) login, `/auth/me`, password change, brute-force rate limiting (production only).
- **Users**: admin-managed CRUD with roles (`admin`, `manager`).
- **Clients**: CRUD, validation, case-insensitive e-mail duplicate protection, search/filter/sort/pagination.
- **Deals**: pipeline with stage transitions (lost requires a reason), value/forecast data.
- **Tasks**: CRUD, filters (mine/overdue), priority/status workflow.
- **Tickets**: support tickets, replies/messages, close/reopen.
- **Analytics**: dashboard KPIs, report, CSV export.
- **Frontend SPA**: login, dashboard, clients, deals, tasks, support, analytics, users pages.

## Tech stack

| Layer | Technologies |
|---|---|
| Backend | FastAPI 0.115.6, Pydantic 2.10.4, SQLAlchemy 2.0.36, Alembic 1.14.0 |
| Authentication | JWT HS256 (`python-jose`), bcrypt via `passlib`, per-IP login rate limiting |
| Database | PostgreSQL 16 (Docker / production), SQLite (local development) |
| API | REST, OpenAPI / Swagger UI at `/api/docs`, standardized error envelope |
| Frontend | Vanilla HTML/CSS/JS SPA — no frameworks, no build step |
| Tooling | Docker Compose, pytest + httpx, uvicorn |

## Screenshots

All pages below are shown with the bundled demo data.

### Dashboard — KPI and activity overview

![Dashboard: KPI cards for clients, won revenue, open pipeline and tickets; revenue overview, upcoming tasks, recent deals and activity](image-1.png)

### Clients — searchable list with filters

![Clients: search, status and segment filters, manager assignment and row actions](image-2.png)

### Deals — Kanban pipeline

![Deals: Kanban board with Qualification, Proposal, Negotiation, Won and Lost stages](image-3.png)

### Tasks — priorities and quick filters

![Tasks: Today, Upcoming, Overdue and Completed filters, priorities, due dates and assignees](image-4.png)

### Support — ticket queue

![Support: ticket list with priority badges, assignees and inline status changes](image-5.png)

### Analytics — reports and CSV export

![Analytics: period KPIs, revenue by stage, monthly won-revenue trend and manager performance](image-6.png)

### Users — team administration

![Users: team members with roles, statuses and management actions](image-7.png)

## Repository layout

```
crmpro/
├── backend/
│   ├── app/               # FastAPI app (api/, core/, db/, models/, schemas/, services/)
│   ├── alembic/           # migrations (versions/18467cddcfb1_initial_schema.py)
│   ├── tests/             # pytest suite (SQLite in-memory fixtures)
│   ├── alembic.ini, pytest.ini, Dockerfile
├── frontend/              # SPA: index.html, css/, js/  (served at / and /static)
├── docker-compose.yml     # db (postgres:16) + migrate (one-shot alembic) + api
├── requirements.txt       # pinned deps (single source of truth)
├── .env.example           # copy to .env
├── README.md, AUDIT.md, IMPLEMENTATION_STATUS.md
├── image-1.png … image-7.png   # UI screenshots (see Screenshots)
└── _smoke_live.py         # local smoke test (15 checks) — run against a live server
```

## Quick start (Docker Compose)

Requires Docker with the Compose plugin.

```bash
git clone https://github.com/Sp0tik/MyProject.git
cd MyProject/2/crmpro

cp .env.example .env          # set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build -d   # db (PostgreSQL 16) → migrations → API on :8000

# load demo data (idempotent): 4 users, 5 clients, deals/tasks/tickets
docker compose exec api python -m app.db.seed seed
```

Open http://localhost:8000/ — interactive API docs at http://localhost:8000/api/docs.

**Demo login:** `admin@crmpro.example` / `Admin123!` (seed data for local use only; create your own
admin with `docker compose exec api python -m app.db.seed create-admin --email you@example.com --password <strong-password>`).

`docker compose down` stops the stack and keeps database data in the `pgdata` volume.
The Compose build context is the repository root (see comments in `docker-compose.yml`).

## Local development (SQLite — zero setup)

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows; use .venv/bin/pip elsewhere

# seed demo data (idempotent): 4 users, 5 clients, deals/tasks/tickets
cd backend
../.venv/Scripts/python -m app.db.seed seed
../.venv/Scripts/python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/ — API docs at http://127.0.0.1:8000/api/docs.

Log in with the demo credentials from the Docker Compose quick start above.

## Tests

From the repo root (either invocation works):

```bash
# 1) from backend/ (recommended)
cd backend && ../.venv/Scripts/python -m pytest

# 2) from repo root
$env:PYTHONPATH='backend'   # PowerShell; export PYTHONPATH=backend on bash
.venv/Scripts/python -m pytest backend/tests
```

Current: **61 passed** (~90 s — bcrypt hashing dominates fixture setup).

## Smoke test (live server)

```bash
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app &   # start API
../.venv/Scripts/python _smoke_live.py                            # 15/15 expected
```

## Configuration (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | dev placeholder | **must** be changed for production |
| `ENVIRONMENT` | `development` | `production` enables login rate limiting |
| `DATABASE_URL` | `sqlite:///./crmpro.db` | e.g. `postgresql+psycopg://user:pass@host:5432/crmpro` |
| `BACKEND_CORS_ORIGINS` | `*` | comma-separated list in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | JWT lifetime |
| `RATE_LIMIT_LOGIN_ATTEMPTS` / `_WINDOW_SECONDS` | `10` / `60` | per-IP, production only |

See [AUDIT.md](AUDIT.md) for verification results and known limitations,
and [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for per-module status.
