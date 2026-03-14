"""Arbeitsagentur (German Federal Employment Agency) REST API adapter."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import httpx

from ...config import AppConfig
from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
_API_KEY = "jobboerse-jobsuche"
_PAGE_SIZE = 25
_DETAIL_WORKERS = 8


class ArbeitsagenturSource(JobSource):
    source_id = "arbeitsagentur"

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        all_jobs: list[RawJob] = []
        seen: set[str] = set()
        headers = {"X-API-Key": _API_KEY, "Accept": "application/json"}

        for query in queries:
            jobs = self._search(query, headers)
            for j in jobs:
                if j.id not in seen:
                    seen.add(j.id)
                    all_jobs.append(j)
        return all_jobs

    def _search(self, query: SearchQuery, headers: dict) -> list[RawJob]:
        max_results = query.extra.get("max_results", 50)
        radius = query.extra.get("radius_km", 50)
        params: dict = {
            "was": query.keyword,
            "wo": query.location if query.location != "Remote" else "",
            "umkreis": radius,
            "size": min(_PAGE_SIZE, max_results),
            "page": 1,
        }
        stubs: list[RawJob] = []
        try:
            with httpx.Client(timeout=30.0) as client:
                while len(stubs) < max_results:
                    resp = client.get(_BASE, headers=headers, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    items = data.get("stellenangebote", [])
                    if not items:
                        break
                    for item in items:
                        job = _map_stub(item)
                        if job:
                            stubs.append(job)
                    if len(stubs) >= data.get("maxErgebnisse", 0) or len(stubs) >= max_results:
                        break
                    params["page"] += 1
        except Exception as exc:
            logger.error("Arbeitsagentur error for '%s': %s", query.keyword, exc)
        return _fetch_details(stubs[:max_results], headers)


def _fetch_details(stubs: list[RawJob], headers: dict) -> list[RawJob]:
    if not stubs:
        return stubs

    def _enrich(job: RawJob) -> RawJob:
        ref_nr = job.raw_extra.get("refnr", "")
        if not ref_nr:
            return job
        try:
            with httpx.Client(timeout=10.0) as c:
                resp = c.get(f"{_BASE}/{ref_nr}", headers=headers)
                resp.raise_for_status()
                d = resp.json()
            parts = [d.get("stellenbeschreibung", "")]
            for k in ("aufgaben", "anforderungen", "angebote"):
                if d.get(k):
                    parts.append(d[k])
            text = "\n\n".join(p for p in parts if p)
            if text:
                job.description = text
        except Exception:
            pass
        return job

    enriched: list[RawJob] = []
    order = {j.id: i for i, j in enumerate(stubs)}
    with ThreadPoolExecutor(max_workers=_DETAIL_WORKERS) as pool:
        for fut in as_completed({pool.submit(_enrich, j): j for j in stubs}):
            enriched.append(fut.result())
    enriched.sort(key=lambda j: order.get(j.id, 9999))
    return enriched


def _map_stub(item: dict) -> RawJob | None:
    try:
        ref_nr = item.get("refnr", "")
        ao = item.get("arbeitsort", {})
        location = ", ".join(filter(None, [ao.get("ort"), ao.get("region")])) or "Germany"
        url = item.get("externeUrl") or f"https://www.arbeitsagentur.de/jobsuche/suche?id={ref_nr}"
        return RawJob(
            id=f"ba-{ref_nr}",
            title=item.get("titel", ""),
            company=item.get("arbeitgeber", ""),
            location=location,
            url=url,
            description=item.get("beruf", ""),
            source="arbeitsagentur",
            date_posted=item.get("aktuelleVeroeffentlichungsdatum", ""),
            job_type="fulltime",
            remote=item.get("homeoffice"),
            raw_extra=item,
        )
    except Exception as exc:
        logger.warning("Failed to parse BA stub: %s", exc)
        return None
