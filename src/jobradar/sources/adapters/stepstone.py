"""StepStone.de direct scraper — httpx + BeautifulSoup.

Parse order: JSON-LD structured data → article cards → stellenangebote links.
Fetches up to 2 pages per query.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}


class StepstoneSource(JobSource):
    source_id = "stepstone"

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
        max_results  = query.extra.get("max_results", 50)
        radius       = query.extra.get("radius_km", 50)
        keyword      = query.keyword
        location     = query.location if query.location != "Remote" else ""
        keyword_slug = urllib.parse.quote_plus(keyword)
        params       = {"radius": radius}

        url = (f"https://www.stepstone.de/jobs/{keyword_slug}/in-{urllib.parse.quote_plus(location)}"
               if location else f"https://www.stepstone.de/work/{keyword_slug}")

        all_jobs: list[RawJob] = []
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url, headers=_HEADERS, params=params)
                if resp.status_code != 200:
                    logger.warning("StepStone returned %d for '%s'", resp.status_code, keyword)
                    return []
                all_jobs.extend(_parse_page(BeautifulSoup(resp.text, "html.parser")))

                if len(all_jobs) < max_results:
                    resp2 = client.get(url, headers=_HEADERS, params={**params, "page": 2})
                    if resp2.status_code == 200:
                        all_jobs.extend(_parse_page(BeautifulSoup(resp2.text, "html.parser")))
        except Exception as e:
            logger.error("StepStone search failed for '%s': %s", keyword, e)
            return []

        logger.info("StepStone: %d jobs for '%s' in '%s'",
                    len(all_jobs), keyword, location or "Germany")
        return all_jobs[:max_results]


def _parse_page(soup: BeautifulSoup) -> list[RawJob]:
    jobs: list[RawJob] = []

    # Strategy 1: JSON-LD structured data
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                for item in data:
                    j = _parse_jsonld(item)
                    if j:
                        jobs.append(j)
            elif isinstance(data, dict):
                if data.get("@type") == "ItemList":
                    for elem in data.get("itemListElement", []):
                        j = _parse_jsonld(elem.get("item", elem))
                        if j:
                            jobs.append(j)
                else:
                    j = _parse_jsonld(data)
                    if j:
                        jobs.append(j)
        except Exception:
            continue
    if jobs:
        return jobs

    # Strategy 2: article elements
    articles = soup.select("article[data-testid]") or soup.select("article")
    for article in articles:
        j = _parse_article(article)
        if j:
            jobs.append(j)
    if jobs:
        return jobs

    # Strategy 3: stellenangebote links
    seen: set[str] = set()
    for link in soup.find_all("a", href=re.compile(r"/stellenangebote--")):
        href = link.get("href", "")
        if not href:
            continue
        full_url = href if href.startswith("http") else f"https://www.stepstone.de{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        title_text = link.get_text(strip=True)
        if title_text and len(title_text) > 5:
            jobs.append(RawJob(
                id=f"stepstone-{abs(hash(full_url)) % 10**8}",
                title=title_text,
                company="", location="", url=full_url,
                description="", source="stepstone",
            ))
    return jobs


def _parse_article(article) -> RawJob | None:
    try:
        title_el = (article.select_one("h2 a")
                    or article.select_one("[data-at='job-item-title']")
                    or article.select_one("a[href*='stellenangebote']"))
        title = title_el.get_text(strip=True) if title_el else ""
        link_el = article.select_one("a[href]")
        href    = link_el.get("href", "") if link_el else ""
        job_url = href if href.startswith("http") else f"https://www.stepstone.de{href}"
        company_el = (article.select_one("[data-at='job-item-company-name']")
                      or article.select_one("span[class*='company']"))
        company = company_el.get_text(strip=True) if company_el else ""
        location_el = (article.select_one("[data-at='job-item-location']")
                       or article.select_one("span[class*='location']"))
        location = location_el.get_text(strip=True) if location_el else ""
        if title:
            return RawJob(
                id=f"stepstone-{abs(hash(job_url)) % 10**8}",
                title=title, company=company, location=location,
                url=job_url, description="", source="stepstone",
            )
    except Exception as e:
        logger.debug("Failed to parse StepStone article: %s", e)
    return None


def _parse_jsonld(data) -> RawJob | None:
    if not isinstance(data, dict) or data.get("@type") != "JobPosting":
        return None
    title = data.get("title", "")
    if not title:
        return None
    company = (data.get("hiringOrganization") or {}).get("name", "")
    location = ""
    loc = data.get("jobLocation", {})
    if isinstance(loc, dict):
        location = (loc.get("address") or {}).get("addressLocality", "")
    elif isinstance(loc, list) and loc:
        location = (loc[0].get("address") or {}).get("addressLocality", "")
    url = data.get("url", "")
    return RawJob(
        id=f"stepstone-{abs(hash(url)) % 10**8}",
        title=title, company=company, location=location, url=url,
        description=(data.get("description") or "")[:500],
        source="stepstone",
        date_posted=data.get("datePosted", ""),
    )
