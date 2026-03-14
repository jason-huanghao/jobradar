"""Jobs router — query scored jobs from DB."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlmodel import select

from ...storage.db import get_session
from ...storage.models import Job, ScoredJobRecord
from ..main import get_config

router = APIRouter()


@router.get("")
def list_jobs(
    min_score: float = Query(default=0.0, ge=0, le=10),
    source: str = Query(default=""),
    status: str = Query(default=""),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Return scored jobs with optional filters, sorted by score descending."""
    cfg = get_config()
    db_path = cfg.resolve_path(cfg.server.db_path)

    with next(get_session(db_path)) as session:
        query = select(ScoredJobRecord, Job).join(Job, ScoredJobRecord.job_id == Job.id)

        if min_score > 0:
            query = query.where(ScoredJobRecord.overall >= min_score)
        if source:
            query = query.where(Job.source.contains(source))
        if status:
            query = query.where(ScoredJobRecord.status == status)

        query = query.order_by(ScoredJobRecord.overall.desc()).offset(offset).limit(limit)
        rows = session.exec(query).all()

    results = []
    for score_rec, job in rows:
        results.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "salary": job.salary,
            "source": job.source,
            "date_posted": job.date_posted,
            "score": score_rec.overall,
            "breakdown": {
                "skills_match": score_rec.skills_match,
                "seniority_fit": score_rec.seniority_fit,
                "location_fit": score_rec.location_fit,
                "language_fit": score_rec.language_fit,
                "visa_friendly": score_rec.visa_friendly,
                "growth_potential": score_rec.growth_potential,
            },
            "reasoning": score_rec.reasoning,
            "application_angle": score_rec.application_angle,
            "status": score_rec.status,
            "applied": score_rec.applied,
        })

    return JSONResponse(content={"jobs": results, "total": len(results)})


@router.get("/{job_id}")
def get_job(job_id: str):
    """Return full detail for a single job including description."""
    cfg = get_config()
    db_path = cfg.resolve_path(cfg.server.db_path)

    with next(get_session(db_path)) as session:
        job = session.get(Job, job_id)
        if not job:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Job not found")
        score = session.exec(
            select(ScoredJobRecord).where(ScoredJobRecord.job_id == job_id)
        ).first()

    return JSONResponse(content={
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "description": job.description,
        "salary": job.salary,
        "source": job.source,
        "date_posted": job.date_posted,
        "score": score.overall if score else None,
        "reasoning": score.reasoning if score else "",
        "application_angle": score.application_angle if score else "",
        "status": score.status if score else "unscored",
    })


@router.patch("/{job_id}/status")
def update_status(job_id: str, status: str = Query(...)):
    """Update the application status for a job."""
    cfg = get_config()
    db_path = cfg.resolve_path(cfg.server.db_path)

    with next(get_session(db_path)) as session:
        record = session.exec(
            select(ScoredJobRecord).where(ScoredJobRecord.job_id == job_id)
        ).first()
        if not record:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Scored job not found")
        record.status = status
        if status == "applied":
            from datetime import datetime
            record.applied = True
            record.applied_at = datetime.utcnow()
        session.add(record)
        session.commit()

    return JSONResponse(content={"ok": True, "job_id": job_id, "status": status})
