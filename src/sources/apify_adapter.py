"""Apify meta-platform adapter (stub — 8000+ actors)."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)


class ApifySource(JobSource):
    name = "apify"

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        logger.warning("Apify source not yet implemented.")
        return []
