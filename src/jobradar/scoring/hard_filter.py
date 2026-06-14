"""Hard filter — eliminate jobs cheaply before any LLM calls."""

from __future__ import annotations

import logging
from datetime import datetime

from ..config import AppConfig
from ..models.job import RawJob
from .freshness import is_too_old

logger = logging.getLogger(__name__)


def apply(jobs: list[RawJob], config: AppConfig) -> tuple[list[RawJob], int]:
    """Run all hard filters. Returns (kept, dropped_count)."""
    kept = []
    dropped = 0
    now = datetime.utcnow()
    ttl_days = config.search.max_days_old
    kw_lower = [k.lower() for k in config.search.exclude_keywords]
    co_lower = [c.lower() for c in config.search.exclude_companies]

    for job in jobs:
        reason = _check(job, now, ttl_days, kw_lower, co_lower)
        if reason:
            logger.debug("DROP [%s] '%s' @ '%s' — %s", job.source, job.title, job.company, reason)
            dropped += 1
        else:
            kept.append(job)

    logger.info("Hard filter: %d kept, %d dropped", len(kept), dropped)
    return kept, dropped


def _check(
    job: RawJob,
    now: datetime,
    ttl_days: int,
    kw_lower: list[str],
    co_lower: list[str],
) -> str | None:
    """Return a reason string if the job should be dropped, else None."""

    # 1. Excluded company
    if co_lower and job.company.lower() in co_lower:
        return "excluded company"

    # 2. Excluded keyword in title or description
    title_lower = job.title.lower()
    desc_lower = (job.description or "").lower()
    for kw in kw_lower:
        if kw in title_lower or kw in desc_lower:
            return f"excluded keyword: {kw}"

    # 3. Too old (posting age) or explicit deadline already passed
    if is_too_old(job.date_posted, job.valid_through, now, ttl_days):
        return f"too old / expired: posted={job.date_posted} deadline={job.valid_through}"

    # 4. Missing essential fields
    if not job.title:
        return "missing title"

    return None
