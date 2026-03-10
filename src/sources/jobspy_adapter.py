"""python-jobspy adapter: wraps scrape_jobs() for Indeed, Google, LinkedIn, Glassdoor."""

from __future__ import annotations

import logging
from datetime import datetime

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)


class JobSpySource(JobSource):
    name = "jobspy"

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        """Search via python-jobspy."""
        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("python-jobspy not installed. Run: pip install python-jobspy")
            return []

        board = query.extra.get("board", "indeed")
        country = query.extra.get("country", "germany")
        max_results = config.search.max_results_per_source

        try:
            logger.info("JobSpy [%s]: searching '%s' in '%s'", board, query.keyword, query.location)

            jobs_df = scrape_jobs(
                site_name=[board],
                search_term=query.keyword,
                location=query.location if query.location != "Remote" else "Germany",
                country_indeed=country,
                results_wanted=max_results,
                hours_old=config.search.max_days_old * 24,
                is_remote=query.location == "Remote",
            )

            if jobs_df is None or jobs_df.empty:
                logger.info("JobSpy [%s]: no results", board)
                return []

            raw_jobs: list[RawJob] = []
            for _, row in jobs_df.iterrows():
                job = _map_row_to_raw_job(row, board)
                if job:
                    raw_jobs.append(job)

            logger.info("JobSpy [%s]: %d jobs found", board, len(raw_jobs))
            return raw_jobs

        except Exception as e:
            logger.error("JobSpy [%s] search failed: %s", board, e)
            return []


def _map_row_to_raw_job(row, board: str) -> RawJob | None:
    """Map a python-jobspy DataFrame row to RawJob."""
    try:
        title = str(row.get("title", "")).strip()
        if not title:
            return None

        company = str(row.get("company_name", row.get("company", ""))).strip()
        location = str(row.get("location", "")).strip()
        url = str(row.get("job_url", row.get("link", ""))).strip()
        description = str(row.get("description", "")).strip()

        date_posted = ""
        dp = row.get("date_posted")
        if dp is not None:
            if isinstance(dp, datetime):
                date_posted = dp.isoformat()
            else:
                date_posted = str(dp)

        salary = ""
        for col in ("min_amount", "max_amount", "salary_source"):
            if row.get(col):
                salary = f"{row.get('min_amount', '')}-{row.get('max_amount', '')} {row.get('currency', 'EUR')}"
                break

        is_remote = bool(row.get("is_remote", False))

        return RawJob(
            id=f"jobspy-{board}-{hash(url) % 10**8}",
            title=title,
            company=company,
            location=location,
            url=url,
            description=description,
            source=f"jobspy:{board}",
            date_posted=date_posted,
            job_type=str(row.get("job_type", "fulltime")),
            salary=salary,
            remote=is_remote,
        )
    except Exception as e:
        logger.warning("Failed to parse JobSpy row: %s", e)
        return None
