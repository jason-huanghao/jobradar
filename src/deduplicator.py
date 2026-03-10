"""Deduplicate job listings using URL match + fuzzy title/company matching."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from rapidfuzz import fuzz

from .models import RawJob

logger = logging.getLogger(__name__)

_FUZZY_THRESHOLD = 85


class Deduplicator:
    """Track seen jobs and deduplicate new batches."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._seen_urls: set[str] = set()
        self._seen_titles: list[tuple[str, str]] = []  # (title_lower, company_lower)
        self._cache_path = cache_dir / "seen_jobs.json" if cache_dir else None
        if self._cache_path:
            self._load_cache()

    def _load_cache(self) -> None:
        if self._cache_path and self._cache_path.exists():
            try:
                data = json.loads(self._cache_path.read_text())
                self._seen_urls = set(data.get("urls", []))
                self._seen_titles = [tuple(t) for t in data.get("titles", [])]
                logger.info("Loaded %d seen URLs from cache", len(self._seen_urls))
            except Exception as e:
                logger.warning("Failed to load dedup cache: %s", e)

    def _save_cache(self) -> None:
        if self._cache_path:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "urls": list(self._seen_urls),
                "titles": list(self._seen_titles),
            }
            self._cache_path.write_text(json.dumps(data, indent=2))

    def deduplicate(self, jobs: list[RawJob]) -> list[RawJob]:
        """Remove duplicates from a batch. Returns unique jobs only."""
        unique: list[RawJob] = []

        for job in jobs:
            # 1. Exact URL match
            url_key = job.dedup_key
            if url_key in self._seen_urls:
                logger.debug("Dedup (URL): %s", job.title)
                continue

            # 2. Fuzzy title + company match
            title_lower = job.title.strip().lower()
            company_lower = job.company.strip().lower()
            is_fuzzy_dup = False

            for seen_title, seen_company in self._seen_titles:
                title_score = fuzz.ratio(title_lower, seen_title)
                company_score = fuzz.ratio(company_lower, seen_company)
                if title_score >= _FUZZY_THRESHOLD and company_score >= _FUZZY_THRESHOLD:
                    logger.debug(
                        "Dedup (fuzzy): '%s @ %s' ≈ '%s @ %s' (%.0f/%.0f)",
                        job.title,
                        job.company,
                        seen_title,
                        seen_company,
                        title_score,
                        company_score,
                    )
                    is_fuzzy_dup = True
                    break

            if is_fuzzy_dup:
                continue

            # Mark as seen
            self._seen_urls.add(url_key)
            self._seen_titles.append((title_lower, company_lower))
            unique.append(job)

        removed = len(jobs) - len(unique)
        if removed:
            logger.info("Dedup: %d/%d removed, %d unique", removed, len(jobs), len(unique))

        self._save_cache()
        return unique
