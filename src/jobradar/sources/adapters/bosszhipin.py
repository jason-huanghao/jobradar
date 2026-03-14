"""BOSS直聘 adapter — cookie-based auth.

Setup:
  1. Log in at https://www.zhipin.com in Chrome.
  2. DevTools → Application → Cookies → copy __zp_stoken__ and wt2.
  3. export BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"
  Or place cookies in memory/bosszhipin_cookies.json as {"__zp_stoken__": "xxx"}.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import httpx

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36")


class BossZhipinSource(JobSource):
    source_id = "bosszhipin"

    def is_enabled(self, config) -> bool:
        return getattr(config.sources.bosszhipin, "enabled", False)

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        cookies = _load_cookies()
        if not cookies:
            logger.warning("BOSS直聘: no cookies — set BOSSZHIPIN_COOKIES env var")
            return []

        headers = {
            "User-Agent": _UA,
            "Referer": "https://www.zhipin.com/web/geek/job",
            "Accept": "application/json",
            "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
        }

        all_jobs: list[RawJob] = []
        seen: set[str] = set()

        for query in queries:
            jobs = self._search(query, headers)
            for j in jobs:
                if j.id not in seen:
                    seen.add(j.id)
                    all_jobs.append(j)
        return all_jobs

    def _search(self, query: SearchQuery, headers: dict) -> list[RawJob]:
        max_results = query.extra.get("max_results", 50)
        delay = query.extra.get("delay_between_requests", 2.0)
        city_code = query.extra.get("city_code", "101010100")
        params = {"scene": 1, "query": query.keyword, "city": city_code,
                  "pageSize": min(30, max_results), "pageIndex": 1}
        jobs: list[RawJob] = []

        with httpx.Client(timeout=20.0) as client:
            while len(jobs) < max_results:
                time.sleep(delay)
                try:
                    resp = client.get(_SEARCH_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    logger.error("BOSS直聘 error: %s", exc)
                    break
                if data.get("code") != 0:
                    logger.warning("BOSS直聘 API code %s", data.get("code"))
                    break
                items = (data.get("zpData") or {}).get("jobList", [])
                if not items:
                    break
                for item in items:
                    job = _parse(item)
                    if job:
                        jobs.append(job)
                if len(items) < params["pageSize"]:
                    break
                params["pageIndex"] += 1
        return jobs[:max_results]


def _load_cookies() -> dict[str, str]:
    env = os.getenv("BOSSZHIPIN_COOKIES", "").strip()
    if env:
        return {k.strip(): v.strip() for part in env.split(";")
                if "=" in part for k, _, v in [part.partition("=")]}
    f = Path("./memory/bosszhipin_cookies.json")
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _parse(item: dict) -> RawJob | None:
    try:
        jid = item.get("encryptJobId", "")
        loc = ", ".join(filter(None, [item.get("cityName"), item.get("areaDistrict"),
                                      item.get("businessDistrict")]))
        labels = item.get("jobLabels", []) + item.get("skills", [])
        desc = "；".join(l for l in labels if isinstance(l, str))
        return RawJob(
            id=f"bosszhipin-{jid}",
            title=item.get("jobName", ""),
            company=item.get("brandName", ""),
            location=loc,
            url=f"https://www.zhipin.com/job_detail/{jid}.html",
            description=desc,
            source="bosszhipin",
            salary=item.get("salaryDesc", ""),
            raw_extra=item,
        )
    except Exception as exc:
        logger.warning("BOSS直聘 parse failed: %s", exc)
        return None
