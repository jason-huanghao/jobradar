"""XING jobs adapter (stub — direct scraper or Apify actor)."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)


class XingSource(JobSource):
    name = "xing"

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        adapter = config.sources.xing.adapter or "apify"
        logger.warning("XING source (%s) not yet implemented.", adapter)
        return []
