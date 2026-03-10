"""XING Jobs direct scraper.

Scrapes XING's public job search pages using httpx + BeautifulSoup.
"""

from __future__ import annotations

import json
import logging
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


class XingSource(JobSource):
    name = "xing"

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        """Search XING Jobs by scraping their public search pages."""
        max_results = config.search.max_results_per_source
        keyword = query.keyword
        location = query.location if query.location != "Remote" else ""

        params = {
            "keywords": keyword,
            "sort": "date",
        }
        if location:
            params["location"] = location

        url = "https://www.xing.com/jobs/search"
        all_jobs = []

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url, headers=_HEADERS, params=params)
                if resp.status_code != 200:
                    logger.warning(
                        "XING returned %d for '%s' in '%s'",
                        resp.status_code, keyword, location,
                    )
                    return []

                soup = BeautifulSoup(resp.text, "html.parser")

                # Try JSON-LD first
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(script.string or "")
                        if isinstance(data, dict) and data.get("@type") == "ItemList":
                            for elem in data.get("itemListElement", []):
                                item = elem.get("item", elem)
                                job = _parse_xing_jsonld(item)
                                if job:
                                    all_jobs.append(job)
                        elif isinstance(data, list):
                            for item in data:
                                job = _parse_xing_jsonld(item)
                                if job:
                                    all_jobs.append(job)
                    except Exception:
                        continue

                # Fallback: parse HTML job cards
                if not all_jobs:
                    cards = (
                        soup.select("[data-testid='job-search-result']")
                        or soup.select("article")
                        or soup.select(".jobsearch-ResultsList li")
                    )
                    for card in cards:
                        job = _parse_xing_card(card)
                        if job:
                            all_jobs.append(job)

                # Fallback: find job links
                if not all_jobs:
                    links = soup.find_all("a", href=lambda h: h and "/jobs/" in h and "/search" not in h)
                    seen = set()
                    for link in links:
                        href = link.get("href", "")
                        if not href or href in seen:
                            continue
                        seen.add(href)
                        full_url = href if href.startswith("http") else f"https://www.xing.com{href}"
                        title = link.get_text(strip=True)
                        if title and len(title) > 5:
                            all_jobs.append(
                                RawJob(
                                    id=f"xing-{hash(full_url) % 10**8}",
                                    title=title,
                                    company="",
                                    location="",
                                    url=full_url,
                                    description="",
                                    source="xing",
                                )
                            )

        except Exception as e:
            logger.error("XING search failed for '%s': %s", keyword, e)
            return []

        logger.info(
            "XING: %d jobs for '%s' in '%s'",
            len(all_jobs), keyword, location or "Germany",
        )
        return all_jobs[:max_results]


def _parse_xing_jsonld(data):
    """Parse a JSON-LD JobPosting from XING."""
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
        id=f"xing-{hash(url) % 10**8}",
        title=title,
        company=company,
        location=location,
        url=url,
        description=(data.get("description", "") or "")[:500],
        source="xing",
        date_posted=data.get("datePosted", ""),
    )


def _parse_xing_card(card):
    """Parse a XING HTML job card."""
    try:
        title_el = card.select_one("h3") or card.select_one("h2") or card.select_one("a")
        title = title_el.get_text(strip=True) if title_el else ""

        link_el = card.select_one("a[href]")
        href = link_el.get("href", "") if link_el else ""
        job_url = href if href.startswith("http") else f"https://www.xing.com{href}"

        company = ""
        location = ""
        spans = card.select("span")
        for span in spans:
            text = span.get_text(strip=True)
            cls = " ".join(span.get("class", []))
            if "company" in cls.lower():
                company = text
            elif "location" in cls.lower():
                location = text

        if title:
            return RawJob(
                id=f"xing-{hash(job_url) % 10**8}",
                title=title,
                company=company,
                location=location,
                url=job_url,
                description="",
                source="xing",
            )
    except Exception as e:
        logger.debug("Failed to parse XING card: %s", e)
    return None
