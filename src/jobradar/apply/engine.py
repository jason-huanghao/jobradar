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
    profile_id: str,
    min_score: float = 7.5,
    dry_run: bool = False,
    daily_limit: int = 50,
    platforms: list[str] | None = None,
    confirm: Callable[[dict], bool] | None = None,
    on_result: Callable[[ApplyResult], None] | None = None,
) -> ApplySession:
    """Apply to all eligible jobs for one profile above min_score.

    Args:
        db_path: Path to SQLite database
        profile_id: Profile whose scored jobs to apply for
        min_score: Only apply to jobs scored at or above this threshold
        dry_run: Preview what would happen — no actual submissions
        daily_limit: Maximum applications per day across all platforms
        platforms: Which platforms to apply on (default: all configured)
        confirm: Optional callback invoked with each job dict; return False
            to skip it. The caller owns any prompting/IO. Not consulted on dry runs.
        on_result: Callback called after each application attempt

    Returns:
        ApplySession with all results
    """
    jobs = _load_eligible_jobs(db_path, profile_id, min_score)
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

        # Confirmation via injected callback (caller owns any prompting/IO)
        if confirm is not None and not dry_run and not confirm(job):
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


def _load_eligible_jobs(db_path: Path, profile_id: str, min_score: float) -> list[dict]:
    """Load scored jobs for one profile, best-first, skipping already-applied."""
    from ..storage.db import get_session, init_db
    from ..storage.repo import list_scored

    init_db(db_path)
    history = ApplyHistory()
    results = []

    with next(get_session(db_path)) as session:
        for score_rec, job in list_scored(session, profile_id, min_score=min_score):
            if history.already_applied(job.id):
                continue
            if not job.url:
                continue
            results.append({
                "id": job.id, "title": job.title, "company": job.company or "",
                "location": job.location or "", "score": round(score_rec.overall, 1),
                "platform": job.source, "url": job.url,
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
