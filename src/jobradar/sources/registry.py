"""Source registry — discovers enabled adapters and runs them in parallel."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from ..config import AppConfig
from ..models.job import RawJob, SearchQuery
from .base import JobSource
from .normalizer import dedup, normalise

logger = logging.getLogger(__name__)

_MAX_WORKERS = 6


class SourceRegistry:
    """Holds all registered adapters. Run fetch_all() to crawl in parallel."""

    def __init__(self) -> None:
        self._sources: dict[str, JobSource] = {}

    def register(self, source: JobSource) -> None:
        self._sources[source.source_id] = source

    def fetch_all(
        self,
        queries: list[SearchQuery],
        config: AppConfig,
        since: datetime,
        on_source_done: callable | None = None,
    ) -> list[RawJob]:
        """Run all enabled sources in parallel threads.

        Args:
            queries:        Full list of SearchQuery objects.
            config:         AppConfig (used to check enabled flags).
            since:          Only return jobs posted after this datetime.
            on_source_done: Optional callback(source_id, jobs_found) for progress.

        Returns:
            Deduplicated list of RawJob (normalised IDs).
        """
        # Group queries by source prefix
        by_source: dict[str, list[SearchQuery]] = {}
        for q in queries:
            key = q.source.split(":")[0]  # "jobspy:indeed" → "jobspy"
            by_source.setdefault(key, []).append(q)

        enabled = {sid: src for sid, src in self._sources.items() if src.is_enabled(config)}
        if not enabled:
            logger.warning("No sources enabled — check config.yaml sources section")
            return []

        all_jobs: list[RawJob] = []

        def _run(source_id: str, src: JobSource) -> tuple[str, list[RawJob]]:
            qs = by_source.get(source_id, [])
            if not qs:
                return source_id, []
            try:
                jobs = src.fetch(qs, since)
                return source_id, jobs
            except Exception as exc:
                logger.error("Source '%s' failed: %s", source_id, exc)
                return source_id, []

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = {pool.submit(_run, sid, src): sid for sid, src in enabled.items()}
            for future in as_completed(futures):
                sid, jobs = future.result()
                normalised = [normalise(j) for j in jobs]
                all_jobs.extend(normalised)
                if on_source_done:
                    on_source_done(sid, len(normalised))
                logger.info("Source '%s': %d jobs", sid, len(normalised))

        result = dedup(all_jobs)
        logger.info("Total after dedup: %d jobs", len(result))
        return result


def build_registry(config: AppConfig) -> SourceRegistry:
    """Instantiate and register all adapters. Import here to avoid circular deps."""
    from .adapters.arbeitsagentur import ArbeitsagenturSource
    from .adapters.bosszhipin import BossZhipinSource
    from .adapters.jobspy_adapter import JobSpySource
    from .adapters.lagou import LagouSource
    from .adapters.stepstone import StepstoneSource
    from .adapters.xing import XingSource
    from .adapters.zhilian import ZhilianSource

    registry = SourceRegistry()
    for src in [
        ArbeitsagenturSource(),
        JobSpySource(),
        BossZhipinSource(),
        LagouSource(),
        ZhilianSource(),
        StepstoneSource(),
        XingSource(),
    ]:
        registry.register(src)
    return registry
