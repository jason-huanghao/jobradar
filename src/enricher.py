"""Job enrichment: add company ratings, extra metadata."""

from __future__ import annotations

import logging

from .models import RawJob

logger = logging.getLogger(__name__)


def enrich_jobs(jobs: list[RawJob]) -> list[RawJob]:
    """Enrich jobs with additional metadata (Kununu ratings, etc.).

    Currently a stub — future versions will integrate Apify Kununu actor
    or web scraping for company ratings.
    """
    logger.info("Enrichment: %d jobs (stub — no enrichment applied)", len(jobs))
    # TODO: Kununu rating lookup via web search or Apify
    # TODO: Glassdoor rating lookup
    # TODO: Company size / funding stage from APIs
    return jobs
