"""StepStone MCP client adapter (stub — requires mcp-stepstone server)."""

from __future__ import annotations

import logging

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)


class StepStoneMCPSource(JobSource):
    name = "stepstone"

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        """Search StepStone via MCP server.

        TODO: Implement MCP client connection to mcp-stepstone.
        For now, this is a stub that logs a warning.
        """
        logger.warning(
            "StepStone MCP source not yet implemented. "
            "Install mcp-stepstone and configure mcp_servers/stepstone_launcher.sh"
        )
        return []
