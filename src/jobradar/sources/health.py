"""Source reliability — single source of truth for per-source outcomes.

A ``SourceOutcome`` records how one source fared on one pipeline run. The
registry builds these; the pipeline persists them to ``PipelineRun.sources_run``;
``storage.repo.recent_source_health`` aggregates recent runs into rolling health.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .base import SourceError

SourceStatus = Literal["ok", "empty", "error", "blocked"]

_MAX_ERROR_LEN = 200


def classify(jobs: int, error: Exception | None) -> SourceStatus:
    """Classify a source's outcome. An error always wins over the job count."""
    if error is not None:
        if isinstance(error, SourceError) and error.blocked:
            return "blocked"
        return "error"
    return "ok" if jobs > 0 else "empty"


def status_is_failure(status: str) -> bool:
    """True for statuses that count as a failure for rolling health."""
    return status in ("error", "blocked")


@dataclass
class SourceOutcome:
    source_id: str
    status: SourceStatus
    jobs: int
    duration_ms: int
    attempts: int = 1
    error: str = ""

    def __post_init__(self) -> None:
        if self.error and len(self.error) > _MAX_ERROR_LEN:
            self.error = self.error[:_MAX_ERROR_LEN]

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "jobs": self.jobs,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SourceOutcome":
        return cls(
            source_id=d.get("source_id", ""),
            status=d.get("status", "empty"),
            jobs=int(d.get("jobs", 0)),
            duration_ms=int(d.get("duration_ms", 0)),
            attempts=int(d.get("attempts", 1)),
            error=d.get("error", ""),
        )
