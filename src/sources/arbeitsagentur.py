"""Arbeitsagentur (German Federal Employment Agency) REST API adapter.

API docs:
  List:   rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs
  Detail: rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs/{refnr}

Uses a static API key: "jobboerse-jobsuche" — no user config needed.
The list endpoint only returns the job category ('beruf'), not the full description.
A second GET to the detail endpoint fetches the full text; we batch these concurrently.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import httpx

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)

_BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
_API_KEY = "jobboerse-jobsuche"
_PAGE_SIZE = 25
_DETAIL_WORKERS = 8   # concurrent detail-fetch threads
_DETAIL_TIMEOUT = 10  # seconds per detail request


class ArbeitsagenturSource(JobSource):
    name = "arbeitsagentur"

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        """Search Arbeitsagentur via their public REST API.

        Two-phase:
          1. List endpoint — fast, returns title/company/location/refnr for up to
             max_results jobs.
          2. Detail endpoint — fetches full job description for each job concurrently
             (_DETAIL_WORKERS threads).  Falls back gracefully if a detail call fails.
        """
        max_results = query.extra.get("max_results", config.search.max_results_per_source)
        radius = query.extra.get("radius_km", config.search.radius_km)

        headers = {
            "X-API-Key": _API_KEY,
            "Accept": "application/json",
        }

        params: dict = {
            "was": query.keyword,
            "wo": query.location if query.location != "Remote" else "",
            "umkreis": radius,
            "size": min(_PAGE_SIZE, max_results),
            "page": 1,
        }

        if config.search.max_days_old:
            params["veroeffentlichtseit"] = config.search.max_days_old

        stub_jobs: list[RawJob] = []   # jobs with category-only description

        try:
            with httpx.Client(timeout=30.0) as client:
                while len(stub_jobs) < max_results:
                    resp = client.get(_BASE_URL, headers=headers, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                    stellenangebote = data.get("stellenangebote", [])
                    if not stellenangebote:
                        break

                    for item in stellenangebote:
                        job = _map_stub(item)
                        if job:
                            stub_jobs.append(job)

                    total = data.get("maxErgebnisse", 0)
                    if len(stub_jobs) >= total or len(stub_jobs) >= max_results:
                        break
                    params["page"] += 1

        except httpx.HTTPStatusError as e:
            logger.error(
                "Arbeitsagentur API error: %s %s",
                e.response.status_code, e.response.text[:200],
            )
        except Exception as e:
            logger.error("Arbeitsagentur search failed: %s", e)

        stub_jobs = stub_jobs[:max_results]
        logger.info(
            "Arbeitsagentur: %d stubs for '%s' in '%s' — fetching details …",
            len(stub_jobs), query.keyword, query.location,
        )

        # Phase 2: enrich with full descriptions concurrently
        all_jobs = _fetch_details(stub_jobs, headers)
        logger.info("Arbeitsagentur: %d jobs with descriptions", len(all_jobs))
        return all_jobs


# ── Detail fetch ───────────────────────────────────────────────────


def _fetch_details(stubs: list[RawJob], headers: dict) -> list[RawJob]:
    """Concurrently fetch full job descriptions for a list of stub jobs.

    Uses the detail endpoint: GET /jobs/{refnr}
    Falls back to the stub (category-word description) on any error.
    """
    if not stubs:
        return stubs

    def _enrich(job: RawJob) -> RawJob:
        ref_nr = job.raw_data.get("refnr", "")
        if not ref_nr:
            return job
        url = f"{_BASE_URL}/{ref_nr}"
        try:
            with httpx.Client(timeout=_DETAIL_TIMEOUT) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                detail = resp.json()
        except Exception as e:
            logger.debug("Detail fetch failed for %s: %s", ref_nr, e)
            return job

        # Extract the free-text description fields from the detail response
        description_parts: list[str] = []
        stellenbeschreibung = detail.get("stellenbeschreibung", "")
        if stellenbeschreibung:
            description_parts.append(stellenbeschreibung)

        # Some listings have a separate tasks / requirements block
        for key in ("aufgaben", "anforderungen", "angebote"):
            val = detail.get(key, "")
            if val:
                description_parts.append(val)

        if description_parts:
            job.description = "\n\n".join(description_parts)

        # Also surface any salary info from the detail response
        if not job.salary:
            lohn = detail.get("verguetung", {})
            if isinstance(lohn, dict):
                low = lohn.get("von")
                high = lohn.get("bis")
                currency = lohn.get("waehrung", "EUR")
                if low or high:
                    job.salary = f"{low or '?'} – {high or '?'} {currency}"

        return job

    enriched: list[RawJob] = []
    with ThreadPoolExecutor(max_workers=_DETAIL_WORKERS) as pool:
        futures = {pool.submit(_enrich, job): job for job in stubs}
        for future in as_completed(futures):
            try:
                enriched.append(future.result())
            except Exception as e:
                logger.warning("Unexpected detail-fetch error: %s", e)
                enriched.append(futures[future])  # keep stub

    # Restore original order (as_completed gives arbitrary order)
    order = {job.id: idx for idx, job in enumerate(stubs)}
    enriched.sort(key=lambda j: order.get(j.id, 9999))
    return enriched


# ── List-endpoint mapper ───────────────────────────────────────────


def _map_stub(item: dict) -> RawJob | None:
    """Map a single Arbeitsagentur list-endpoint item to a RawJob stub."""
    try:
        ref_nr = item.get("refnr", "")
        title = item.get("titel", "")
        company = item.get("arbeitgeber", "")

        arbeitsort = item.get("arbeitsort", {})
        location_parts = []
        if arbeitsort.get("ort"):
            location_parts.append(arbeitsort["ort"])
        if arbeitsort.get("region"):
            location_parts.append(arbeitsort["region"])
        location = ", ".join(location_parts) or "Germany"

        url = f"https://www.arbeitsagentur.de/jobsuche/suche?id={ref_nr}"
        if item.get("externeUrl"):
            url = item["externeUrl"]

        date_posted = item.get(
            "eintrittsdatum", item.get("aktuelleVeroeffentlichungsdatum", "")
        )

        return RawJob(
            id=f"ba-{ref_nr}",
            title=title,
            company=company,
            location=location,
            url=url,
            # 'beruf' is a category label only (e.g. "Softwareentwickler").
            # Phase-2 detail fetch overwrites this with the full description.
            description=item.get("beruf", ""),
            source="arbeitsagentur",
            date_posted=date_posted,
            job_type="fulltime",
            remote=item.get("homeoffice", None),
            raw_data=item,
        )
    except Exception as e:
        logger.warning("Failed to parse BA stub: %s", e)
        return None
