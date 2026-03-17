"""Pipeline router — trigger runs and check run history."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import select

from ...pipeline import JobRadarPipeline
from ...storage.db import get_session
from ...storage.models import PipelineRun
from ..main import get_config

router = APIRouter()


class RunRequest(BaseModel):
    mode: str = "full"  # full | quick | score-only | dry-run


@router.post("/run")
def trigger_run(req: RunRequest):
    """Start a pipeline run synchronously and return the result.

    For long runs use the WebSocket endpoint /ws/pipeline for live progress.
    """
    cfg = get_config()
    pipeline = JobRadarPipeline(cfg)
    result = pipeline.run(mode=req.mode)
    return JSONResponse(content={
        "run_id": result.run_id,
        "status": result.status,
        "jobs_fetched": result.jobs_fetched,
        "jobs_new": result.jobs_new,
        "jobs_scored": result.jobs_scored,
        "jobs_generated": result.jobs_generated,
        "error": result.error,
    })


@router.get("/history")
def run_history(limit: int = 20):
    """Return recent pipeline run records."""
    cfg = get_config()
    db_path = cfg.resolve_path(cfg.server.db_path)

    with next(get_session(db_path)) as session:
        runs = session.exec(
            select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)
        ).all()

    return JSONResponse(content={"runs": [
        {
            "id": r.id,
            "mode": r.mode,
            "status": r.status,
            "jobs_fetched": r.jobs_fetched,
            "jobs_new": r.jobs_new,
            "jobs_scored": r.jobs_scored,
            "jobs_generated": r.jobs_generated,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "error": r.error,
        }
        for r in runs
    ]})


@router.get("/status")
def pipeline_status():
    """Return the latest run status."""
    cfg = get_config()
    db_path = cfg.resolve_path(cfg.server.db_path)

    with next(get_session(db_path)) as session:
        latest = session.exec(
            select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(1)
        ).first()

    if not latest:
        return JSONResponse(content={"status": "never_run"})

    return JSONResponse(content={
        "status": latest.status,
        "last_run": latest.started_at.isoformat() if latest.started_at else None,
        "jobs_scored": latest.jobs_scored,
    })
