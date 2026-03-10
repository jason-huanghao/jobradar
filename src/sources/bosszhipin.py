"""BOSS直聘 (BOSS Zhipin) job source adapter.

Uses httpx with cookie-based authentication.

Setup (one-time):
  1. Log in to https://www.zhipin.com in Chrome.
  2. Open DevTools → Application → Cookies → copy __zp_stoken__ and wt2.
  3. Set env vars:
       export BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"
  Or place them in memory/bosszhipin_cookies.json as {"__zp_stoken__": "xxx", "wt2": "yyy"}.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import httpx

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
_DETAIL_URL = "https://www.zhipin.com/wapi/zpgeek/job/detail.json"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class BossZhipinSource(JobSource):
    """BOSS直聘 scraper using the unofficial JSON search API."""

    name = "bosszhipin"

    def __init__(self) -> None:
        self._cookie_file = Path("./memory/bosszhipin_cookies.json")

    def _load_cookies(self) -> dict[str, str]:
        # Priority 1: env var  BOSSZHIPIN_COOKIES="k1=v1; k2=v2"
        env_cookies = os.getenv("BOSSZHIPIN_COOKIES", "").strip()
        if env_cookies:
            parsed: dict[str, str] = {}
            for part in env_cookies.split(";"):
                part = part.strip()
                if "=" in part:
                    k, _, v = part.partition("=")
                    parsed[k.strip()] = v.strip()
            if parsed:
                return parsed

        # Priority 2: JSON file
        if self._cookie_file.exists():
            try:
                return json.loads(self._cookie_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load BOSS直聘 cookies: %s", e)
        return {}

    def is_enabled(self, config: AppConfig) -> bool:
        return getattr(config.sources.bosszhipin, "enabled", False)

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        cookies = self._load_cookies()
        if not cookies:
            logger.warning(
                "BOSS直聘: no cookies found. "
                "Set BOSSZHIPIN_COOKIES env var or create memory/bosszhipin_cookies.json. "
                "See src/sources/bosszhipin.py header for instructions."
            )
            return []

        max_results = query.extra.get("max_results", config.search.max_results_per_source)
        delay = query.extra.get("delay_between_requests",
                                config.sources.bosszhipin.delay_between_requests)
        city_code = query.extra.get("city_code", config.sources.bosszhipin.city_code)

        headers = {
            "User-Agent": _USER_AGENT,
            "Referer": "https://www.zhipin.com/web/geek/job",
            "Accept": "application/json, text/plain, */*",
            "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
        }

        params = {
            "scene": 1,
            "query": query.keyword,
            "city": city_code,
            "pageSize": min(30, max_results),
            "pageIndex": 1,
        }

        jobs: list[RawJob] = []
        with httpx.Client(timeout=20.0) as client:
            while len(jobs) < max_results:
                try:
                    time.sleep(delay)
                    resp = client.get(_SEARCH_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError as e:
                    logger.error("BOSS直聘 HTTP error: %s", e.response.status_code)
                    break
                except Exception as e:
                    logger.error("BOSS直聘 search failed: %s", e)
                    break

                if data.get("code") != 0:
                    logger.warning("BOSS直聘 API error code %s: %s",
                                   data.get("code"), data.get("message", ""))
                    break

                job_list = (data.get("zpData") or {}).get("jobList", [])
                if not job_list:
                    break

                for item in job_list:
                    job = _parse_job(item)
                    if job:
                        jobs.append(job)

                if len(job_list) < params["pageSize"]:
                    break
                params["pageIndex"] += 1

        logger.info("BOSS直聘: %d jobs for '%s'", len(jobs), query.keyword)
        return jobs[:max_results]


def _parse_job(item: dict) -> RawJob | None:
    try:
        job_id = item.get("encryptJobId", "")
        title = item.get("jobName", "")
        company = item.get("brandName", "")

        loc_parts = [item.get("cityName", ""), item.get("areaDistrict", ""),
                     item.get("businessDistrict", "")]
        location = ", ".join(p for p in loc_parts if p)

        salary = item.get("salaryDesc", "")
        url = f"https://www.zhipin.com/job_detail/{job_id}.html"

        description_parts = [
            item.get("jobLabels", []),   # list of label strings
            item.get("skills", []),
        ]
        desc_labels = []
        for part in description_parts:
            if isinstance(part, list):
                desc_labels.extend(part)
        description = "；".join(desc_labels) if desc_labels else ""

        return RawJob(
            id=f"bosszhipin-{job_id}",
            title=title,
            company=company,
            location=location,
            url=url,
            description=description,
            source="bosszhipin",
            date_posted="",
            job_type="fulltime",
            salary=salary,
            raw_data=item,
        )
    except Exception as e:
        logger.warning("Failed to parse BOSS直聘 job: %s", e)
        return None
