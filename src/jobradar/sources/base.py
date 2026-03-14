"""Abstract base class for all job source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models.job import RawJob


class JobSource(ABC):
    """Every adapter must implement this interface."""

    source_id: str = "base"

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
