"""python-jobspy adapter: Indeed, Google Jobs, Glassdoor, LinkedIn."""
from __future__ import annotations

import logging
from datetime import datetime

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)


class JobSpySource(JobSource):
    source_id = "jobspy"

    def is_enabled(self, config) -> bool:
        return getattr(config.sources.jobspy, "enabled", False)

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("python-jobspy not installed: pip install python-jobspy")
            return []

        all_jobs: list[RawJob] = []
        seen: set[str] = set()
        days_old = max(1, (datetime.utcnow() - since).days)

        for query in queries:
            board   = query.extra.get("board", "indeed")
            country = query.extra.get("country", "germany")
            max_r   = query.extra.get("max_results", 50)
            try:
                df = scrape_jobs(
                    site_name=[board],
                    search_term=query.keyword,
                    location=query.location if query.location != "Remote" else "Germany",
                    country_indeed=country,
                    results_wanted=max_r,
                    hours_old=days_old * 24,
                    is_remote=query.location == "Remote",
                )
            except Exception as e:
                logger.error("JobSpy [%s] '%s': %s", board, query.keyword, e)
                continue

            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                job = _map_row(row, board)
                if job and job.id not in seen:
                    seen.add(job.id)
                    all_jobs.append(job)

        return all_jobs


def _map_row(row, board: str) -> RawJob | None:
    try:
        title = str(row.get("title", "")).strip()
        if not title:
            return None
        url = str(row.get("job_url", row.get("link", ""))).strip()
        salary = ""
        if row.get("min_amount"):
            salary = (f"{row.get('min_amount', '')}-{row.get('max_amount', '')} "
                      f"{row.get('currency', 'EUR')}")
        dp = row.get("date_posted")
        date_posted = dp.isoformat() if isinstance(dp, datetime) else str(dp or "")
        return RawJob(
            id=f"jobspy-{board}-{abs(hash(url)) % 10**10}",
            title=title,
            company=str(row.get("company_name", row.get("company", ""))).strip(),
            location=str(row.get("location", "")).strip(),
            url=url,
            description=str(row.get("description", "")).strip(),
            source=f"jobspy:{board}",
            date_posted=date_posted,
            job_type=str(row.get("job_type", "fulltime")),
            salary=salary,
            remote=bool(row.get("is_remote", False)),
        )
    except Exception as e:
        logger.warning("JobSpy row parse failed: %s", e)
        return None
