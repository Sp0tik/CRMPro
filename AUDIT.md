# CRMPro Audit Report

**Date:** 2026-10-15 · **Environment:** Windows, Python 3.11.2, Node 20.20.2, venv at `.venv/`
**Scope:** full project — backend, tests, frontend, migrations, Docker, docs, repo hygiene.

## Verification results

| # | Check | Method | Result |
|---|-------|--------|--------|
| 1 | Unit/integration tests | `pytest backend/tests -q` | ✅ **61 passed, 0 failed** (86.7 s) |
| 2 | Python syntax/imports | `py_compile` over `backend/app`, `backend/alembic`, `backend/tests` | ✅ **34/34 OK** |
| 3 | Frontend JS syntax | `node --check` over `frontend/js/*.js` | ✅ **13/13 OK** |
| 4 | Compose file | `yaml.safe_load` of `docker-compose.yml` | ✅ valid, services `db`, `migrate`, `api` |
| 5 | Database | SQLite `backend/crmpro.db` | ✅ migrated (`18467cddcfb1`), seeded (4 users, 5 clients) |
| 6 | Alembic | `backend/alembic/` | ✅ `env.py`, `script.py.mako`, initial migration present |
| 7 | Live smoke | uvicorn up + `_smoke_live.py` | ✅ **15/15** (health, SPA, static, docs, auth 401/200, RBAC, CRUD, analytics) |
| 8 | Server log | stderr after run | ✅ no errors (only known passlib warning, see below) |

## Defects found and fixed

1. **Docker image build would fail (blocking).**
   `backend/Dockerfile` ran `COPY requirements.txt .` while compose used
   `build: context: ./backend` — `requirements.txt` lives at the repo root, outside that
   context, so `docker compose build` always failed.
   **Fix:** compose now builds with `context: .` + `dockerfile: backend/Dockerfile`
   (both `migrate` and `api`); Dockerfile now does `COPY backend/ .` and additionally
   `COPY frontend/ /frontend/` so the SPA is served in the container
   (`main.py` resolves the frontend dir to `/frontend` from `/app/app/main.py`).
2. **`.dockerignore` patterns wrong for root context.** `.pytest_cache` → `**/.pytest_cache`,
   added `.qodo`, duplicate `_*.log` ignored; patterns now match the root build context.
3. **Stray empty directories removed:** `alembic/` (empty `versions/` at repo root, the real
   migrations live in `backend/alembic/`), `static/`, `scripts/` — all unreferenced by code
   (the `/static` URL is served from `frontend/`).
4. **Scratch artifacts deleted:** all `backend/_*.txt|_*.bat`, root `_pytest_*.txt`,
   `_tc_result.txt`, `_js_check.txt`, `_py_check.txt`, `_db_check.txt`, `_docker_check.txt`,
   `_smoke_out.txt`, `_server_*.log`, `get-pip.py`.
5. **Docs created:** `README.md`, `AUDIT.md`, `IMPLEMENTATION_STATUS.md` (none existed).

## Test invocation note (fixed during audit)

Running `pytest` from the repo root failed with `ModuleNotFoundError: No module named 'app'`
because `backend/` was not on `sys.path` (`backend/` is intentionally not a package).
Both working invocations are documented in README: from `backend/`, or from the root with
`PYTHONPATH=backend`. No code change was needed.

## Known limitations (not blockers)

- **Docker not installed on the audit machine** — `docker compose build/up` could not be
  executed here. The compose file is YAML-validated and the build-context defect above is
  fixed by inspection; run `docker compose up --build` on a Docker host to confirm end-to-end.
- **`passlib 1.7.4` + `bcrypt 4.2.1` warning:** on startup, `error reading bcrypt version`
  (trapped `AttributeError` inside passlib). Hashing/verification work correctly (all auth
  tests pass). Harmless; to silence it, downgrade to `bcrypt==4.0.1` or migrate off passlib.
- **Test suite runtime ~90 s:** dominated by bcrypt hashing in per-test fixtures
  (~1.5 s setup each). Functionally fine; could be reduced by lowering the hash cost in tests.
- **Git:** the parent repo (`D:/My project/MyProject`) tracks this workspace; the `crmpro/`
  directory is currently **untracked** — nothing has been committed in this audit.
- **Legacy `CRMpro.html`** (single-file SPA prototype) kept at the root for reference; the
  live UI is `frontend/`. Remove it if you no longer need the prototype.

## Security posture

- No hard-coded secrets; `.env` is git-ignored, `.env.example` has placeholders only.
- Dev-only defaults (`SECRET_KEY`, SQLite, CORS `*`) are clearly labelled; production
  requires env overrides — compose enforces `ENVIRONMENT=production` for the API container.
- Login rate limiting active only in production (documented in `main.py`); error handlers
  return generic JSON without stack traces; Postgres port bound to `127.0.0.1`.
- Non-root `appuser` in the container; DB/API dependency chain uses healthcheck gating.
