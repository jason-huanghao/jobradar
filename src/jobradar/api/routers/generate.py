"""Generate router — CV optimization and cover letter on demand, scoped to a user's active profile."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import select

from ...llm.client import LLMClient
from ...models.candidate import CandidateProfile
from ...models.job import RawJob, ScoreBreakdown, ScoredJob
from ...scoring.generator.cover_letter import generate_cover_letter
from ...scoring.generator.cv_optimizer import optimize_cv
from ...storage.db import get_session
from ...storage.models import Application, Job, Score
from ...storage.repo import get_active_profile
from ..deps import get_db_path, get_user_email
from ..main import get_config

router = APIRouter()


def _load_profile(cfg) -> CandidateProfile:
    cache_dir = cfg.resolve_path(cfg.server.cache_dir)
    profile_file = cache_dir / "candidate_profile.json"
    if not profile_file.exists():
        raise HTTPException(status_code=404, detail="No profile found. Upload a CV first.")
    return CandidateProfile(**json.loads(profile_file.read_text()))


@router.post("/application/{job_id}")
def generate_application(
    job_id: str,
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    """Generate optimized CV + cover letter for a specific job."""
    cfg = get_config()
    llm = LLMClient(cfg.llm.text)
    profile = _load_profile(cfg)

    with next(get_session(db_path)) as session:
        db_profile = get_active_profile(session, user_email)
        if db_profile is None:
            raise HTTPException(status_code=404, detail="No active profile")
        profile_id = db_profile.id
        job_rec = session.get(Job, job_id)
        if not job_rec:
            raise HTTPException(status_code=404, detail="Job not found")
        score_rec = session.get(Score, (profile_id, job_id))

    raw_job = RawJob(
        id=job_rec.id, title=job_rec.title, company=job_rec.company,
        location=job_rec.location, url=job_rec.url, description=job_rec.description,
        source=job_rec.source, salary=job_rec.salary or "",
    )
    scored = ScoredJob(
        job=raw_job,
        score=score_rec.overall if score_rec else 0.0,
        breakdown=ScoreBreakdown() if not score_rec else ScoreBreakdown(
            skills_match=score_rec.skills_match,
            seniority_fit=score_rec.seniority_fit,
            location_fit=score_rec.location_fit,
            language_fit=score_rec.language_fit,
            visa_friendly=score_rec.visa_friendly,
            growth_potential=score_rec.growth_potential,
        ),
        application_angle=score_rec.application_angle if score_rec else "",
    )

    cv_md, gaps = optimize_cv(raw_job, profile, llm)
    cl_md = generate_cover_letter(scored, profile, llm)

    with next(get_session(db_path)) as session:
        app = Application(
            profile_id=profile_id, job_id=job_id,
            cv_optimized_md=cv_md,
            cover_letter_md=cl_md,
            gaps=json.dumps(gaps),
        )
        session.add(app)
        session.commit()
        session.refresh(app)

    return JSONResponse(content={
        "job_id": job_id,
        "cv_optimized_md": cv_md,
        "cover_letter_md": cl_md,
        "gaps": gaps,
        "application_id": app.id,
    })


@router.get("/application/{job_id}")
def get_application(
    job_id: str,
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    """Return the most recent generated application for a job, for this user's active profile."""
    with next(get_session(db_path)) as session:
        db_profile = get_active_profile(session, user_email)
        if db_profile is None:
            raise HTTPException(status_code=404, detail="No application generated yet.")
        app = session.exec(
            select(Application)
            .where(Application.profile_id == db_profile.id, Application.job_id == job_id)
            .order_by(Application.created_at.desc())
            .limit(1)
        ).first()

    if not app:
        raise HTTPException(status_code=404, detail="No application generated yet.")

    return JSONResponse(content={
        "job_id": job_id,
        "cv_optimized_md": app.cv_optimized_md,
        "cover_letter_md": app.cover_letter_md,
        "gaps": json.loads(app.gaps or "[]"),
        "status": app.status,
        "created_at": app.created_at.isoformat(),
    })
