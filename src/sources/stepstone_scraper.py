"""StepStone.de direct scraper — no MCP dependency needed.

Scrapes StepStone's public job search pages using httpx + BeautifulSoup.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse

import httpx
from bs4 import BeautifulSoup

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
}


class StepStoneSource(JobSource):
    name = "stepstone"

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        """Search StepStone.de by scraping their public search pages."""
        max_results = config.search.max_results_per_source
        keyword = query.keyword
        location = query.location if query.location != "Remote" else ""
        radius = query.extra.get("radius_km", config.search.radius_km)

        keyword_slug = urllib.parse.quote_plus(keyword)
        params = {"radius": radius}

        if location:
            location_slug = urllib.parse.quote_plus(location)
            url = f"https://www.stepstone.de/jobs/{keyword_slug}/in-{location_slug}"
        else:
            url = f"https://www.stepstone.de/work/{keyword_slug}"

        all_jobs = []

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url, headers=_HEADERS, params=params)
                if resp.status_code != 200:
                    logger.warning(
                        "StepStone returned %d for '%s' in '%s'",
                        resp.status_code, keyword, location,
                    )
                    return []

                soup = BeautifulSoup(resp.text, "html.parser")
                jobs = _parse_listing_page(soup)
                all_jobs.extend(jobs)

                if len(all_jobs) < max_results:
                    params["page"] = 2
                    resp2 = client.get(url, headers=_HEADERS, params=params)
                    if resp2.status_code == 200:
                        soup2 = BeautifulSoup(resp2.text, "html.parser")
                        all_jobs.extend(_parse_listing_page(soup2))

        except Exception as e:
            logger.error("StepStone search failed for '%s': %s", keyword, e)
            return []

        logger.info(
            "StepStone: %d jobs for '%s' in '%s'",
            len(all_jobs), keyword, location or "Germany",
        )
        return all_jobs[:max_results]


def _parse_listing_page(soup):
    """Parse job listings from a StepStone search results page."""
    jobs = []

    # Strategy 1: JSON-LD structured data (most reliable)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                for item in data:
                    job = _parse_jsonld(item)
                    if job:
                        jobs.append(job)
            elif isinstance(data, dict):
                if data.get("@type") == "ItemList":
                    for elem in data.get("itemListElement", []):
                        job = _parse_jsonld(elem.get("item", elem))
                        if job:
                            jobs.append(job)
                else:
                    job = _parse_jsonld(data)
                    if job:
                        jobs.append(job)
        except Exception:
            continue

    if jobs:
        return jobs

    # Strategy 2: article elements
    articles = soup.select("article[data-testid]") or soup.select("article")
    for article in articles:
        job = _parse_article(article)
        if job:
            jobs.append(job)

    if jobs:
        return jobs

    # Strategy 3: stellenangebote links
    links = soup.find_all("a", href=re.compile(r"/stellenangebote--"))
    seen = set()
    for link in links:
        href = link.get("href", "")
        if not href:
            continue
        full_url = href if href.startswith("http") else f"https://www.stepstone.de{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        title_text = link.get_text(strip=True)
        if title_text and len(title_text) > 5:
            jobs.append(
                RawJob(
                    id=f"stepstone-{hash(full_url) % 10**8}",
                    title=title_text,
                    company="",
                    location="",
                    url=full_url,
                    description="",
                    source="stepstone",
                )
            )

    return jobs


def _parse_article(article):
    """Parse a single article element into a RawJob."""
    try:
        title_el = (
            article.select_one("h2 a")
            or article.select_one("[data-at='job-item-title']")
            or article.select_one("a[href*='stellenangebote']")
        )
        title = title_el.get_text(strip=True) if title_el else ""

        link_el = article.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""
        job_url = href if href.startswith("http") else f"https://www.stepstone.de{href}"

        company_el = (
            article.select_one("[data-at='job-item-company-name']")
            or article.select_one("span[class*='company']")
        )
        company = company_el.get_text(strip=True) if company_el else ""

        location_el = (
            article.select_one("[data-at='job-item-location']")
            or article.select_one("span[class*='location']")
        )
        location = location_el.get_text(strip=True) if location_el else ""

        if title:
            return RawJob(
                id=f"stepstone-{hash(job_url) % 10**8}",
                title=title,
                company=company,
                location=location,
                url=job_url,
                description="",
                source="stepstone",
            )
    except Exception as e:
        logger.debug("Failed to parse StepStone article: %s", e)
    return None


def _parse_jsonld(data):
    """Parse a JSON-LD JobPosting object."""
    if not isinstance(data, dict) or data.get("@type") != "JobPosting":
        return None
    title = data.get("title", "")
    if not title:
        return None
    company = ""
    org = data.get("hiringOrganization", {})
    if isinstance(org, dict):
        company = org.get("name", "")
    location = ""
    loc = data.get("jobLocation", {})
    if isinstance(loc, dict):
        addr = loc.get("address", {})
        if isinstance(addr, dict):
            location = addr.get("addressLocality", "")
    elif isinstance(loc, list) and loc:
        addr = loc[0].get("address", {})
        if isinstance(addr, dict):
            location = addr.get("addressLocality", "")
    url = data.get("url", "")

    return RawJob(
        id=f"stepstone-{hash(url) % 10**8}",
        title=title,
        company=company,
        location=location,
        url=url,
        description=(data.get("description", "") or "")[:500],
        source="stepstone",
        date_posted=data.get("datePosted", ""),
    )
