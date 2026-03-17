"""Apply engine — orchestrates all platform appliers against the job DB."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from .base import ApplyResult, ApplySession, ApplyStatus
from .history import ApplyHistory

logger = logging.getLogger(__name__)


def run_apply(
    *,
    db_path: Path,
    min_score: float = 7.5,
    dry_run: bool = False,
    confirm_each: bool = False,
    daily_limit: int = 50,
    platforms: list[str] | None = None,
    on_result: Callable[[ApplyResult], None] | None = None,
) -> ApplySession:
    """Apply to all eligible jobs in the DB above min_score.

    Args:
        db_path: Path to SQLite database
        min_score: Only apply to jobs scored at or above this threshold
        dry_run: Preview what would happen — no actual submissions
        confirm_each: Interactively confirm each job before applying
        daily_limit: Maximum applications per day across all platforms
        platforms: Which platforms to apply on (default: all configured)
        on_result: Callback called after each application attempt

    Returns:
        ApplySession with all results
    """
    jobs = _load_eligible_jobs(db_path, min_score)
    history = ApplyHistory()
    session = ApplySession()

    if not jobs:
        logger.info("No eligible jobs found (min_score=%.1f)", min_score)
        return session

    appliers = _build_appliers(history, daily_limit, platforms or ["bosszhipin", "linkedin"])

    for job in jobs:
        # Check global daily limit across all platforms
        if history.daily_count() >= daily_limit:
            logger.info("Daily limit %d reached — stopping", daily_limit)
            break

        # Find the right applier
        applier = next((a for a in appliers if a.can_apply(job)), None)
        if applier is None:
            continue

        # Interactive confirm
        if confirm_each and not dry_run:
            print(f"\n[{job['score']:.1f}] {job['title']} @ {job['company']} ({job['platform']})")
            print(f"  URL: {job['url']}")
            ans = input("  Apply? [y/N] ").strip().lower()
            if ans != "y":
                result = ApplyResult(
                    job_id=job["id"], title=job["title"],
                    company=job.get("company", ""), platform=job["platform"],
                    status=ApplyStatus.SKIPPED, message="user skipped",
                )
                session.results.append(result)
                if on_result:
                    on_result(result)
                continue

        result = applier.apply(job, dry_run=dry_run)
        session.results.append(result)
        if on_result:
            on_result(result)

        logger.info("%s: %s — %s", result.status.value, result.title, result.message)

    return session


def _load_eligible_jobs(db_path: Path, min_score: float) -> list[dict]:
    """Load scored jobs from DB, sorted best-first, skipping already-applied."""
    from sqlmodel import select
    from ..storage.db import get_session, init_db
    from ..storage.models import Job, ScoredJobRecord

    init_db(db_path)
    history = ApplyHistory()
    results = []

    with next(get_session(db_path)) as session:
        scored = session.exec(select(ScoredJobRecord)).all()
        job_map = {j.id: j for j in session.exec(select(Job)).all()}

        for s in scored:
            if s.overall < min_score:
                continue
            if history.already_applied(s.job_id):
                continue
            j = job_map.get(s.job_id)
            if not j or not j.url:
                continue
            results.append({
                "id": s.job_id,
                "title": j.title,
                "company": j.company or "",
                "location": j.location or "",
                "score": round(s.overall, 1),
                "platform": j.source,
                "url": j.url,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def _build_appliers(history: ApplyHistory, daily_limit: int, platforms: list[str]) -> list:
    appliers = []
    if "bosszhipin" in platforms:
        from .boss import BossZhipinApplier
        appliers.append(BossZhipinApplier(daily_limit=daily_limit, history=history))
    if "linkedin" in platforms:
        from .linkedin import LinkedInApplier
        appliers.append(LinkedInApplier(daily_limit=daily_limit, history=history))
    return appliers
