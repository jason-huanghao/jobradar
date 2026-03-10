"""FastAPI web application for JobRadar CV upload system.

This module provides REST API endpoints for:
- CV upload
- Job status checking
- Job results retrieval
- User management
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from ..config import AppConfig, load_config
from ..models import ScoredJob
from .api import upload, status, jobs
from .services.job_processor import JobProcessor


# Create FastAPI app
app = FastAPI(
    title="JobRadar API",
    description="AI-powered job search with multi-platform support",
    version="0.2.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
web_ui_dir = Path(__file__).parent.parent.parent / "web_ui"
if web_ui_dir.exists():
    static_dir = web_ui_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)))
    app.mount("/", StaticFiles(directory=str(web_ui_dir), html=True))
# Global job processor instance
job_processor: Optional[JobProcessor] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global job_processor

    config = load_config()
    job_processor = JobProcessor(config)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global job_processor
    if job_processor:
        await job_processor.shutdown()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "jobradar-web",
    }


@app.get("/")
async def root():
    """Serve index page."""
    index_path = web_ui_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return JSONResponse(
        {
            "message": "JobRadar API",
            "version": "0.2.0",
            "endpoints": {
                "upload": "/api/upload",
                "status": "/api/status/{job_id}",
                "jobs": "/api/jobs/{job_id}",
                "health": "/health",
            },
        }
    )


# Include API routers
app.include_router(upload.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")


def create_app() -> FastAPI:
    """Factory function to create and configure the app."""
    return app
