"""Abstract base class for all job source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models.job import RawJob


class SourceError(Exception):
    """Raised by an adapter on a hard, whole-source failure (HTTP non-200,
    network error). Lets the registry distinguish a genuine failure from a
    source that legitimately returned no matches. Set ``blocked=True`` when the
    failure looks like an anti-bot block (HTTP 403/429)."""

    def __init__(self, message: str, *, blocked: bool = False) -> None:
        super().__init__(message)
        self.blocked = blocked


class JobSource(ABC):
    """Every adapter must implement this interface."""

    source_id: str = "base"
    kind: str = "scraper"            # api | library | scraper — reliability taxonomy

    @abstractmethod
    def fetch(
        self,
        queries: list,           # list[SearchQuery]
        since: datetime,
    ) -> list[RawJob]:
        """Fetch jobs matching the queries, posted after `since`.

        Returns raw dicts that will be normalised by the registry.
        Implementations should handle their own errors and return []
        rather than raising, to allow other sources to continue.
        """
        ...

    def is_enabled(self, config) -> bool:  # config: AppConfig
        src = getattr(config.sources, self.source_id, None)
        return bool(src and getattr(src, "enabled", False))
