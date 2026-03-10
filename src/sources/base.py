"""Abstract base class for all job data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import AppConfig
from ..models import RawJob, SearchQuery


class JobSource(ABC):
    """Interface that every job source adapter must implement."""

    name: str = "base"

    @abstractmethod
    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        """Execute a search query and return raw job listings."""
        ...

    def is_enabled(self, config: AppConfig) -> bool:
        """Check if this source is enabled in config."""
        source_cfg = getattr(config.sources, self.name, None)
        return source_cfg.enabled if source_cfg else False
