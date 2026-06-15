"""Query helpers for user / profile / score scoping. Pure functions over a Session."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlmodel import Session, select

from ..scoring.freshness import is_expired
from ..sources.health import SourceOutcome, status_is_failure
from .models import Job, PipelineRun, Profile, Score, User, UserSettings


def resolve_or_create_user(session: Session, email: str, display_name: str = "") -> User:
    user = session.get(User, email)
    if user is None:
        user = User(email=email, display_name=display_name)
        session.add(user)
        session.flush()
    return user


def create_profile_version(
    session: Session, user_email: str, cv_source: str, profile_json: str
) -> Profile:
    """Create a new active profile version, deactivating any prior ones."""
    existing = session.exec(
        select(Profile).where(Profile.user_email == user_email)
    ).all()
    for p in existing:
        p.is_active = False
        session.add(p)
    next_version = max((p.version for p in existing), default=0) + 1
    profile = Profile(
        id=uuid.uuid4().hex,
        user_email=user_email,
        version=next_version,
        cv_source=cv_source,
        profile_json=profile_json,
        is_active=True,
    )
    session.add(profile)
    session.flush()
    return profile


def get_active_profile(session: Session, user_email: str) -> Profile | None:
    return session.exec(
        select(Profile)
        .where(Profile.user_email == user_email, Profile.is_active == True)  # noqa: E712
    ).first()


def get_user_settings(session: Session, user_email: str) -> UserSettings | None:
    return session.get(UserSettings, user_email)


def upsert_user_settings(
    session: Session, user_email: str, *,
    provider: str = "", model: str = "", base_url: str = "", api_key_env: str = "",
) -> UserSettings:
    """Create or update a user's LLM endpoint selection. Ensures the user exists."""
    resolve_or_create_user(session, user_email)
    row = session.get(UserSettings, user_email)
    if row is None:
        row = UserSettings(user_email=user_email)
    row.provider = provider
    row.model = model
    row.base_url = base_url
    row.api_key_env = api_key_env
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def scored_job_ids(session: Session, profile_id: str) -> set[str]:
    return set(session.exec(
        select(Score.job_id).where(Score.profile_id == profile_id)
    ).all())


def list_scored(session: Session, profile_id: str, min_score: float = 0.0,
                include_expired: bool = False):
    """Return list[(Score, Job)] for a profile, score-descending.
    Expired jobs are hidden unless include_expired is True."""
    query = (
        select(Score, Job)
        .join(Job, Score.job_id == Job.id)
        .where(Score.profile_id == profile_id)
    )
    if not include_expired:
        query = query.where(Job.status != "expired")
    if min_score > 0:
        query = query.where(Score.overall >= min_score)
    query = query.order_by(Score.overall.desc())
    return session.exec(query).all()


def recent_source_health(session: Session, limit: int = 20) -> dict[str, dict]:
    """Aggregate per-source health from the most recent pipeline runs.

    Reads the last `limit` PipelineRun rows (newest first) and folds their
    `sources_run` outcomes into, per source_id:
        last_status, last_jobs, last_run_at, last_ok_at, consecutive_failures.
    `consecutive_failures` counts error/blocked outcomes from the newest run
    backwards until the first non-failure for that source."""
    runs = session.exec(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)
    ).all()

    health: dict[str, dict] = {}
    streak_open: dict[str, bool] = {}   # still counting consecutive failures?

    for run in runs:  # newest → oldest
        try:
            raw = json.loads(run.sources_run or "[]")
        except (ValueError, TypeError):
            continue
        for d in raw:
            o = SourceOutcome.from_dict(d)
            sid = o.source_id
            if sid not in health:
                health[sid] = {
                    "last_status": o.status,
                    "last_jobs": o.jobs,
                    "last_run_at": run.started_at,
                    "last_ok_at": None,
                    "consecutive_failures": 0,
                }
                streak_open[sid] = True
            h = health[sid]
            if h["last_ok_at"] is None and o.status == "ok":
                h["last_ok_at"] = run.started_at
            if streak_open[sid]:
                if status_is_failure(o.status):
                    h["consecutive_failures"] += 1
                else:
                    streak_open[sid] = False
    return health


def sweep_expired(session: Session, now: datetime, staleness_days: int) -> int:
    """Flip active jobs whose deadline passed or that went stale to expired.
    Flag only — never deletes. Idempotent. Returns the number flipped."""
    jobs = session.exec(select(Job).where(Job.status == "active")).all()
    count = 0
    for job in jobs:
        if is_expired(job.expires_at, job.last_seen_at, now, staleness_days):
            job.status = "expired"
            session.add(job)
            count += 1
    session.commit()
    return count
