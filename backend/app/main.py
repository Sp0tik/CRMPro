"""FastAPI application entrypoint.

Wires routers, CORS, a simple in-memory rate limiter for the login endpoint,
and standardized error handlers that never leak stack traces / internals.
"""
import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analytics, auth, clients, deals, tasks, tickets, users
from app.core.config import settings

logger = logging.getLogger("crmpro")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# --- CORS --------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Simple in-memory rate limiter for sensitive endpoints -------------------
class RateLimiter:
    """Fixed-window counter keyed by client IP. Adequate for a single-process
    deployment; use a shared store (e.g. Redis) when scaling horizontally."""

    def __init__(self, max_events: int, window_seconds: int):
        self.max_events = max_events
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_events:
            return False
        q.append(now)
        return True


login_limiter = RateLimiter(settings.RATE_LIMIT_LOGIN_ATTEMPTS, settings.RATE_LIMIT_WINDOW_SECONDS)


@app.middleware("http")
async def rate_limit_login(request: Request, call_next):
    # Disabled in test/dev so automated tests are not throttled; the limiter
    # is enforced in production (ENVIRONMENT=production).
    if settings.ENVIRONMENT == "production" and request.url.path.endswith(
        "/auth/login"
    ) and request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        if not login_limiter.allow(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many login attempts. Please try again later."},
            )
    return await call_next(request)


# --- Routers -----------------------------------------------------------------
API = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=API)
app.include_router(users.router, prefix=API)
app.include_router(clients.router, prefix=API)
app.include_router(deals.router, prefix=API)
app.include_router(tasks.router, prefix=API)
app.include_router(tickets.router, prefix=API)
app.include_router(analytics.router, prefix=API)


# --- Static frontend (SPA) ----------------------------------------------------
# The built frontend lives in ../frontend and is served under /static with the
# SPA entry at /. If the directory is absent (e.g. API-only deploy) this is
# skipped gracefully.
import os  # noqa: E402

_FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)
if os.path.isdir(_FRONTEND_DIR):
    from fastapi.staticfiles import StaticFiles

    _index = os.path.join(_FRONTEND_DIR, "index.html")

    @app.get("/", include_in_schema=False)
    def serve_index():
        from fastapi.responses import FileResponse

        return FileResponse(_index)

    # Mounted last so it does not shadow /api routes.
    app.mount(
        "/static",
        StaticFiles(directory=_FRONTEND_DIR),
        name="static",
    )


# --- Health ------------------------------------------------------------------
@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/api/health/db", tags=["health"])
def health_db() -> dict:
    from sqlalchemy import text

    from app.db.session import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("DB health check failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "database": "unreachable"},
        )


# --- Generic error handlers (never leak internals) ---------------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
