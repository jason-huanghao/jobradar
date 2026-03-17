"""XING Jobs direct scraper — httpx + BeautifulSoup.

Parse order: JSON-LD → HTML cards → job-URL link fallback.
Fetches up to 2 pages per query, deduplicates by URL.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}
_MIN_TITLE_LEN = 8


class XingSource(JobSource):
    source_id = "xing"

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        all_jobs: list[RawJob] = []
        seen: set[str] = set()
        for query in queries:
            jobs = self._search(query)
            for j in jobs:
                if j.id not in seen:
                    seen.add(j.id)
                    all_jobs.append(j)
        return all_jobs

    def _search(self, query: SearchQuery) -> list[RawJob]:
        max_results = query.extra.get("max_results", 50)
        keyword     = query.keyword
        location    = query.location if query.location != "Remote" else ""

        base_params: dict = {"keywords": keyword, "sort": "date"}
        if location:
            base_params["location"] = location

        url      = "https://www.xing.com/jobs/search"
        all_jobs: list[RawJob] = []
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url, headers=_HEADERS, params=base_params)
                if resp.status_code != 200:
                    logger.warning("XING returned %d for '%s'", resp.status_code, keyword)
                    return []
                all_jobs.extend(_parse_page(BeautifulSoup(resp.text, "html.parser")))

                if len(all_jobs) < max_results:
                    p2 = client.get(url, headers=_HEADERS, params={**base_params, "page": 2})
                    if p2.status_code == 200:
                        all_jobs.extend(_parse_page(BeautifulSoup(p2.text, "html.parser")))
        except Exception as e:
            logger.error("XING search failed for '%s': %s", keyword, e)
            return []

        # Deduplicate by URL
        seen: set[str] = set()
        unique: list[RawJob] = []
        for job in all_jobs:
            if job.url not in seen:
                seen.add(job.url)
                unique.append(job)
        logger.info("XING: %d jobs for '%s' in '%s'",
                    len(unique), keyword, location or "Germany")
        return unique[:max_results]


def _parse_page(soup: BeautifulSoup) -> list[RawJob]:
    jobs: list[RawJob] = []

    # Strategy 1: JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                for elem in data.get("itemListElement", []):
                    j = _parse_jsonld(elem.get("item", elem))
                    if j:
                        jobs.append(j)
            elif isinstance(data, list):
                for item in data:
                    j = _parse_jsonld(item)
                    if j:
                        jobs.append(j)
        except Exception:
            continue
    if jobs:
        return jobs

    # Strategy 2: HTML job cards
    cards = (soup.select("[data-testid='job-search-result']")
             or soup.select("article")
             or soup.select(".jobsearch-ResultsList li"))
    for card in cards:
        j = _parse_card(card)
        if j:
            jobs.append(j)
    if jobs:
        return jobs

    # Strategy 3: job-URL links
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href: str = link["href"]
        if "/jobs/" not in href or "/search" in href or "/find" in href:
            continue
        full_url = href if href.startswith("http") else f"https://www.xing.com{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        title = link.get_text(strip=True)
        if len(title) >= _MIN_TITLE_LEN:
            jobs.append(RawJob(
                id=f"xing-{abs(hash(full_url)) % 10**8}",
                title=title, company="", location="",
                url=full_url, description="", source="xing",
            ))
    return jobs


def _parse_jsonld(data) -> RawJob | None:
    if not isinstance(data, dict) or data.get("@type") != "JobPosting":
        return None
    title = data.get("title", "")
    if not title:
        return None
    company  = (data.get("hiringOrganization") or {}).get("name", "")
    loc      = data.get("jobLocation", {})
    location = ""
    if isinstance(loc, dict):
        location = (loc.get("address") or {}).get("addressLocality", "")
    elif isinstance(loc, list) and loc:
        location = (loc[0].get("address") or {}).get("addressLocality", "")
    url = data.get("url", "")
    return RawJob(
        id=f"xing-{abs(hash(url)) % 10**8}",
        title=title, company=company, location=location, url=url,
        description=(data.get("description") or "")[:500],
        source="xing",
        date_posted=data.get("datePosted", ""),
    )


def _parse_card(card) -> RawJob | None:
    try:
        title_el = card.select_one("h3") or card.select_one("h2") or card.select_one("a")
        title    = title_el.get_text(strip=True) if title_el else ""
        if len(title) < _MIN_TITLE_LEN:
            return None
        link_el = card.select_one("a[href]")
        href    = link_el["href"] if link_el else ""
        job_url = href if href.startswith("http") else f"https://www.xing.com{href}"
        company = location = ""
        for span in card.select("span"):
            text = span.get_text(strip=True)
            cls  = " ".join(span.get("class", []))
            if "company" in cls.lower():
                company  = text
            elif "location" in cls.lower():
                location = text
        return RawJob(
            id=f"xing-{abs(hash(job_url)) % 10**8}",
            title=title, company=company, location=location,
            url=job_url, description="", source="xing",
        )
    except Exception as e:
        logger.debug("Failed to parse XING card: %s", e)
        return None
