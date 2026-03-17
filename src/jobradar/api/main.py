"""FastAPI application — factory function + middleware setup."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..config import AppConfig, load_config
from ..storage.db import init_db

logger = logging.getLogger(__name__)

_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    db_path = cfg.resolve_path(cfg.server.db_path)
    init_db(db_path)
    logger.info("JobRadar API started — DB: %s", db_path)
    yield
    logger.info("JobRadar API shutting down")


def create_app(config: AppConfig | None = None) -> FastAPI:
    global _config
    if config:
        _config = config

    app = FastAPI(
        title="JobRadar API",
        version="0.2.0",
        description="AI-powered job search agent",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    from .routers.generate import router as generate_router
    from .routers.jobs import router as jobs_router
    from .routers.outputs import router as outputs_router
    from .routers.pipeline import router as pipeline_router
    from .routers.profile import router as profile_router

    app.include_router(profile_router,  prefix="/api/profile",  tags=["profile"])
    app.include_router(jobs_router,     prefix="/api/jobs",     tags=["jobs"])
    app.include_router(pipeline_router, prefix="/api/pipeline", tags=["pipeline"])
    app.include_router(generate_router, prefix="/api/generate", tags=["generate"])
    app.include_router(outputs_router,  prefix="/api/outputs",  tags=["outputs"])

    # WebSocket
    from .ws import router as ws_router
    app.include_router(ws_router)

    # Serve Alpine.js dashboard as SPA
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
