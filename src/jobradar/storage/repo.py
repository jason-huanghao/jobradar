"""Query helpers for user / profile / score scoping. Pure functions over a Session."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Session, select

from ..scoring.freshness import is_expired
from .models import Job, Profile, Score, User


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


def scored_job_ids(session: Session, profile_id: str) -> set[str]:
    return set(session.exec(
        select(Score.job_id).where(Score.profile_id == profile_id)
    ).all())


def list_scored(session: Session, profile_id: str, min_score: float = 0.0):
    """Return list[(Score, Job)] for a profile, score-descending."""
    query = (
        select(Score, Job)
        .join(Job, Score.job_id == Job.id)
        .where(Score.profile_id == profile_id)
    )
    if min_score > 0:
        query = query.where(Score.overall >= min_score)
    query = query.order_by(Score.overall.desc())
    return session.exec(query).all()


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
