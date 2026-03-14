"""StepStone adapter — stub, to be implemented."""

from __future__ import annotations

import logging
from datetime import datetime

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)


class StepstoneSource(JobSource):
    source_id = "stepstone"

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        logger.warning(
            "StepStone adapter is not yet implemented. "
            "Contributions welcome — see docs/CONTRIBUTING.md"
        )
        return []
