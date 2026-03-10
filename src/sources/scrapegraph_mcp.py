"""ScrapeGraph MCP adapter (stub — fallback for arbitrary URLs)."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)


class ScrapeGraphSource(JobSource):
    name = "scrapegraph"

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        logger.warning("ScrapeGraph source not yet implemented.")
        return []
