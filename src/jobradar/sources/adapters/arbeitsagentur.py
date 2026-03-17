"""Arbeitsagentur (German Federal Employment Agency) REST API adapter.

Phase 1: list endpoint (title/company/refnr) — paginated.
Phase 2: detail endpoint — full description + salary fetched concurrently (shared client).
Public API key, no auth needed.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import httpx

from ...config import AppConfig
from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_BASE_URL       = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
_API_KEY        = "jobboerse-jobsuche"
_PAGE_SIZE      = 25
_DETAIL_WORKERS = 8
_DETAIL_TIMEOUT = 10


class ArbeitsagenturSource(JobSource):
    source_id = "arbeitsagentur"

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        all_jobs: list[RawJob] = []
        seen: set[str] = set()
        headers = {"X-API-Key": _API_KEY, "Accept": "application/json"}
        max_days = (datetime.utcnow() - since).days or 30

        for query in queries:
            jobs = self._search(query, headers, max_days)
            for j in jobs:
                if j.id not in seen:
                    seen.add(j.id)
                    all_jobs.append(j)
        return all_jobs

    def _search(self, query: SearchQuery, headers: dict, max_days: int) -> list[RawJob]:
        max_results = query.extra.get("max_results", 50)
        radius      = query.extra.get("radius_km", 50)
        params: dict = {
            "was":                query.keyword,
            "wo":                 query.location if query.location != "Remote" else "",
            "umkreis":            radius,
            "size":               min(_PAGE_SIZE, max_results),
            "page":               1,
            "veroeffentlichtseit": max_days,
        }
        stubs: list[RawJob] = []
        try:
            with httpx.Client(timeout=30.0) as client:
                while len(stubs) < max_results:
                    resp = client.get(_BASE_URL, headers=headers, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    page_items = data.get("stellenangebote", [])
                    if not page_items:
                        break
                    for item in page_items:
                        stub = _map_stub(item)
                        if stub:
                            stubs.append(stub)
                    total = data.get("maxErgebnisse", 0)
                    if len(stubs) >= total or len(stubs) >= max_results:
                        break
                    params["page"] += 1
        except httpx.HTTPStatusError as e:
            logger.error("Arbeitsagentur API error %d: %s", e.response.status_code,
                         e.response.text[:200])
        except Exception as e:
            logger.error("Arbeitsagentur search failed for '%s': %s", query.keyword, e)

        stubs = stubs[:max_results]
        logger.info("Arbeitsagentur: %d stubs for '%s' — enriching…", len(stubs), query.keyword)
        with httpx.Client(timeout=_DETAIL_TIMEOUT) as detail_client:
            return _fetch_details(stubs, headers, detail_client)


def _fetch_details(stubs: list[RawJob], headers: dict, client: httpx.Client) -> list[RawJob]:
    if not stubs:
        return stubs

    def _enrich(job: RawJob) -> RawJob:
        ref_nr = job.raw_extra.get("refnr", "")
        if not ref_nr:
            return job
        try:
            resp = client.get(f"{_BASE_URL}/{ref_nr}", headers=headers)
            resp.raise_for_status()
            detail = resp.json()
        except Exception as e:
            logger.debug("Detail fetch failed for %s: %s", ref_nr, e)
            return job
        parts = []
        for key in ("stellenbeschreibung", "aufgaben", "anforderungen", "angebote"):
            val = detail.get(key, "")
            if val:
                parts.append(val)
        if parts:
            job.description = "\n\n".join(parts)
        if not job.salary:
            lohn = detail.get("verguetung", {})
            if isinstance(lohn, dict):
                low, high, cur = lohn.get("von"), lohn.get("bis"), lohn.get("waehrung", "EUR")
                if low or high:
                    job.salary = f"{low or '?'} – {high or '?'} {cur}"
        return job

    order    = {job.id: idx for idx, job in enumerate(stubs)}
    enriched: list[RawJob] = []
    with ThreadPoolExecutor(max_workers=_DETAIL_WORKERS) as pool:
        futures = {pool.submit(_enrich, job): job for job in stubs}
        for fut in as_completed(futures):
            try:
                enriched.append(fut.result())
            except Exception as e:
                logger.warning("Enrichment error: %s", e)
                enriched.append(futures[fut])
    enriched.sort(key=lambda j: order.get(j.id, 9999))
    return enriched


def _map_stub(item: dict) -> RawJob | None:
    try:
        ref_nr  = item.get("refnr", "")
        ao      = item.get("arbeitsort", {})
        loc_parts = [p for p in (ao.get("ort"), ao.get("region")) if p]
        location  = ", ".join(loc_parts) or "Germany"
        url = item.get("externeUrl") or \
              f"https://www.arbeitsagentur.de/jobsuche/suche?id={ref_nr}"
        date_posted = item.get("eintrittsdatum",
                               item.get("aktuelleVeroeffentlichungsdatum", ""))
        return RawJob(
            id=f"ba-{ref_nr}",
            title=item.get("titel", ""),
            company=item.get("arbeitgeber", ""),
            location=location,
            url=url,
            description=item.get("beruf", ""),
            source="arbeitsagentur",
            date_posted=date_posted,
            job_type="fulltime",
            remote=item.get("homeoffice"),
            raw_extra=item,
        )
    except Exception as e:
        logger.warning("Failed to parse BA stub: %s", e)
        return None
