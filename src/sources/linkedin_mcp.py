"""LinkedIn MCP client adapter (stub — requires manual login setup)."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)


class LinkedInMCPSource(JobSource):
    name = "linkedin"

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        """Search LinkedIn via MCP server.

        Supports two adapters:
        - stickerdaniel: browser-based, richer data
        - rayyan: API-based, has resume/cover letter gen
        """
        adapter = config.sources.linkedin.adapter or "stickerdaniel"
        logger.warning(
            "LinkedIn MCP source (%s) not yet implemented. "
            "Enable with caution — rate-limited.",
            adapter,
        )
        return []
