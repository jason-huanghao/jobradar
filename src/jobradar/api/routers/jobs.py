"""Jobs router — query scored jobs for the active profile of a user."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from ...storage.db import get_session
from ...storage.models import Job, Score
from ...storage.repo import get_active_profile, list_scored
from ..deps import get_db_path, get_user_email

router = APIRouter()


@router.get("")
def list_jobs(
    min_score: float = Query(default=0.0, ge=0, le=10),
    source: str = Query(default=""),
    status: str = Query(default=""),
    include_expired: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    with next(get_session(db_path)) as session:
        profile = get_active_profile(session, user_email)
        if profile is None:
            return JSONResponse(content={"jobs": [], "total": 0})
        rows = list_scored(session, profile.id, min_score=min_score,
                           include_expired=include_expired)

    results = []
    for score_rec, job in rows:
        if source and source not in job.source:
            continue
        if status and score_rec.status != status:
            continue
        results.append({
            "id": job.id, "title": job.title, "company": job.company,
            "location": job.location, "url": job.url, "salary": job.salary,
            "source": job.source, "date_posted": job.date_posted,
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

    page = results[offset: offset + limit]
    return JSONResponse(content={"jobs": page, "total": len(page)})


@router.get("/{job_id}")
def get_job(
    job_id: str,
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    with next(get_session(db_path)) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        profile = get_active_profile(session, user_email)
        score = None
        if profile is not None:
            score = session.get(Score, (profile.id, job_id))

    return JSONResponse(content={
        "id": job.id, "title": job.title, "company": job.company,
        "location": job.location, "url": job.url, "description": job.description,
        "salary": job.salary, "source": job.source, "date_posted": job.date_posted,
        "score": score.overall if score else None,
        "reasoning": score.reasoning if score else "",
        "application_angle": score.application_angle if score else "",
        "status": score.status if score else "unscored",
    })


@router.patch("/{job_id}/status")
def update_status(
    job_id: str,
    status: str = Query(...),
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    with next(get_session(db_path)) as session:
        profile = get_active_profile(session, user_email)
        if profile is None:
            raise HTTPException(status_code=404, detail="No active profile")
        record = session.get(Score, (profile.id, job_id))
        if not record:
            raise HTTPException(status_code=404, detail="Scored job not found")
        record.status = status
        if status == "applied":
            record.applied = True
            record.applied_at = datetime.now(timezone.utc)
        session.add(record)
        session.commit()

    return JSONResponse(content={"ok": True, "job_id": job_id, "status": status})
