"""Source registry — discovers enabled adapters and runs them in parallel."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from ..config import AppConfig
from ..models.job import RawJob, SearchQuery
from .base import JobSource, SourceError
from .health import SourceOutcome, classify
from .normalizer import dedup, normalise

logger = logging.getLogger(__name__)

_MAX_WORKERS = 6


def _fetch_with_retries(
    src: JobSource, qs: list[SearchQuery], since: datetime,
    max_attempts: int, base_delay: float,
) -> tuple[list[RawJob], Exception | None, int]:
    """Call src.fetch, retrying only on transient SourceError. Returns
    (jobs, last_error_or_None, attempts_used)."""
    attempts = 0
    last_error: Exception | None = None
    for attempt in range(1, max(1, max_attempts) + 1):
        attempts = attempt
        try:
            return src.fetch(qs, since), None, attempts
        except SourceError as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(base_delay * 2 ** (attempt - 1))
                continue
            return [], exc, attempts
        except Exception as exc:  # non-transient: record once, no retry
            return [], exc, attempts
    return [], last_error, attempts


class SourceRegistry:
    """Holds all registered adapters. Run fetch_all() to crawl in parallel.

    After each fetch_all, ``self.last_outcomes`` holds a SourceOutcome per
    source that ran (used for health reporting / PipelineRun.sources_run)."""

    def __init__(self) -> None:
        self._sources: dict[str, JobSource] = {}
        self.last_outcomes: list[SourceOutcome] = []

    def register(self, source: JobSource) -> None:
        self._sources[source.source_id] = source

    @property
    def sources(self) -> dict[str, JobSource]:
        """All registered adapters, keyed by source_id (read-only copy)."""
        return dict(self._sources)

    def fetch_all(
        self,
        queries: list[SearchQuery],
        config: AppConfig,
        since: datetime,
        on_source_done: callable | None = None,
    ) -> list[RawJob]:
        # Group queries by source prefix (e.g. "jobspy:indeed" → "jobspy")
        by_source: dict[str, list[SearchQuery]] = {}
        for q in queries:
            key = q.source.split(":")[0]
            by_source.setdefault(key, []).append(q)

        enabled = {sid: src for sid, src in self._sources.items() if src.is_enabled(config)}
        if not enabled:
            logger.warning("No sources enabled — check config.yaml sources section")
            self.last_outcomes = []
            return []

        max_attempts = config.reliability.max_attempts
        base_delay = config.reliability.retry_base_delay

        all_jobs: list[RawJob] = []
        outcomes: list[SourceOutcome] = []

        def _run(source_id: str, src: JobSource) -> tuple[SourceOutcome, list[RawJob]]:
            qs = by_source.get(source_id, [])
            started = time.monotonic()
            if not qs:
                return SourceOutcome(source_id, "empty", 0, 0), []
            jobs, error, attempts = _fetch_with_retries(
                src, qs, since, max_attempts, base_delay
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            if error is not None:
                logger.error("Source '%s' failed: %s", source_id, error)
            outcome = SourceOutcome(
                source_id=source_id,
                status=classify(len(jobs), error),
                jobs=len(jobs),
                duration_ms=duration_ms,
                attempts=attempts,
                error=str(error) if error else "",
            )
            return outcome, jobs

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = {pool.submit(_run, sid, src): sid for sid, src in enabled.items()}
            for future in as_completed(futures):
                outcome, jobs = future.result()
                normalised = [normalise(j) for j in jobs]
                all_jobs.extend(normalised)
                outcomes.append(outcome)
                if on_source_done:
                    on_source_done(outcome.source_id, len(normalised))
                logger.info("Source '%s': %d jobs (%s)",
                            outcome.source_id, len(normalised), outcome.status)

        self.last_outcomes = outcomes
        result = dedup(all_jobs)
        logger.info("Total after dedup: %d jobs", len(result))
        return result


def build_registry(config: AppConfig) -> SourceRegistry:
    """Instantiate and register all adapters."""
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
        StepstoneSource(),
        XingSource(),
        BossZhipinSource(),
        LagouSource(),
        ZhilianSource(),
    ]:
        registry.register(src)
    return registry
