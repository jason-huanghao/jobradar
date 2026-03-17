"""Apply engine base — result models and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class ApplyStatus(str, Enum):
    APPLIED   = "applied"
    SKIPPED   = "skipped"     # already applied, or below threshold
    FAILED    = "failed"      # network/auth error
    BLOCKED   = "blocked"     # CAPTCHA, rate-limit, inactive HR
    DRY_RUN   = "dry_run"     # dry-run mode, no actual submission


@dataclass
class ApplyResult:
    job_id: str
    title: str
    company: str
    platform: str
    status: ApplyStatus
    message: str = ""


@dataclass
class ApplySession:
    results: list[ApplyResult] = field(default_factory=list)
    daily_count: int = 0

    @property
    def applied(self) -> list[ApplyResult]:
        return [r for r in self.results if r.status == ApplyStatus.APPLIED]

    @property
    def summary(self) -> str:
        counts = {}
        for r in self.results:
            counts[r.status.value] = counts.get(r.status.value, 0) + 1
        parts = [f"{v} {k}" for k, v in sorted(counts.items())]
        return ", ".join(parts) if parts else "no results"


class Applier(Protocol):
    """Interface all platform appliers must implement."""
    platform: str

    def can_apply(self, job: dict) -> bool: ...
    def apply(self, job: dict, *, dry_run: bool = False) -> ApplyResult: ...
    def close(self) -> None: ...
