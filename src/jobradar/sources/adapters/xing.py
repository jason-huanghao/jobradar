"""XING adapter — stub, to be implemented."""

from __future__ import annotations

import logging
from datetime import datetime

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)


class XingSource(JobSource):
    source_id = "xing"

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        logger.warning(
            "XING adapter is not yet implemented. "
            "Contributions welcome — see docs/CONTRIBUTING.md"
        )
        return []
