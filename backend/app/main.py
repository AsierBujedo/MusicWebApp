"""FastAPI application entrypoint.

Wires together configuration, database, routers, CORS, security headers, and the
background request worker. The frontend talks to this service exclusively through
the ``/api/*`` contract defined in ``types/api.ts``.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.bootstrap import ensure_bootstrap_admin
from app.config import settings
from app.database import Base, engine
from app.routers import (
    admin,
    auth,
    bingo,
    catalog,
    covers,
    events,
    favorites,
    health,
    history,
    playback,
    replay,
    playlists,
    requests,
    search,
    spotify,
    stream,
    tracks,
)
from app.services.worker import run_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _init_database() -> None:
    """Create tables when not using Alembic (SQLite dev). For Postgres, prefer
    running ``alembic upgrade head``; ``create_all`` is a no-op for existing
    tables so it stays safe either way."""
    # Import models so every table is registered on the metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_database()
    ensure_bootstrap_admin()

    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(run_worker(stop_event))
    logger.info("%s started (env=%s)", settings.app_name, settings.app_env)
    try:
        yield
    finally:
        stop_event.set()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline defense-in-depth response headers."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    # Hide interactive docs in production; keep them in development.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(SecurityHeadersMiddleware)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,  # session cookie must be sent cross-origin
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register routers.
for module in (auth, search, tracks, stream, covers, catalog, requests, favorites, playlists, history, spotify, events, playback, replay, bingo, admin, health):
    app.include_router(module.router)

# Keep the documented container probe stable while the frontend continues to
# use the namespaced public API route (/api/health).
app.add_api_route("/health", health.health, methods=["GET"], include_in_schema=False)


@app.get("/", include_in_schema=False)
def root():
    return {"service": settings.app_name, "status": "ok"}
