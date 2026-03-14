"""拉勾网 adapter."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import httpx

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_COOKIE_FILE = Path("./memory/lagou_cookies.json")
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class LagouSource(JobSource):
    source_id = "lagou"

    def is_enabled(self, config) -> bool:
        return getattr(config.sources.lagou, "enabled", False)

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        cookies = _get_or_fetch_cookies()
        if not cookies:
            logger.warning("拉勾网: no cookies available")
            return []

        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        headers = {
            "User-Agent": _UA,
            "Referer": "https://www.lagou.com/jobs/list",
            "Origin": "https://www.lagou.com",
            "Cookie": cookie_str,
        }

        all_jobs: list[RawJob] = []
        seen: set[str] = set()

        for query in queries:
            delay = query.extra.get("delay_between_requests", 2.0)
            city_code = query.extra.get("city_code", "101020100")
            max_results = query.extra.get("max_results", 50)

            time.sleep(delay)
            try:
                with httpx.Client(follow_redirects=True) as client:
                    resp = client.post(
                        "https://www.lagou.com/jobs/v2/positionAjax.json",
                        json={"first": "true", "pn": 1, "kd": query.keyword,
                              "city": city_code, "needAddtionalResult": "false"},
                        headers=headers,
                        timeout=30.0,
                    )
                if resp.status_code != 200 or not resp.json().get("success"):
                    continue
                items = (resp.json().get("content", {})
                         .get("positionResult", {}).get("result", []))
                for item in items[:max_results]:
                    job = _parse(item)
                    if job and job.id not in seen:
                        seen.add(job.id)
                        all_jobs.append(job)
            except Exception as exc:
                logger.error("拉勾网 error for '%s': %s", query.keyword, exc)

        return all_jobs


def _get_or_fetch_cookies() -> dict[str, str]:
    if _COOKIE_FILE.exists():
        try:
            return json.loads(_COOKIE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Auto-fetch session cookies
    try:
        with httpx.Client(follow_redirects=True) as client:
            resp = client.get("https://www.lagou.com/", timeout=30.0)
            cookies = dict(resp.cookies)
            if cookies:
                _COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
                _COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))
                logger.info("拉勾网: fetched and cached %d cookies", len(cookies))
                return cookies
    except Exception as exc:
        logger.error("拉勾网 cookie fetch failed: %s", exc)
    return {}


def _parse(item: dict) -> RawJob | None:
    try:
        jid = item.get("positionId", "")
        sal_min = item.get("salaryMin", "")
        sal_max = item.get("salaryMax", "")
        salary = f"{sal_min}-{sal_max}K" if sal_min and sal_max else item.get("salary", "")
        skills = item.get("skillLables", [])
        exp = item.get("workYear", "")
        edu = item.get("education", "")
        desc = f"{exp} experience required. {edu}. Skills: {', '.join(skills)}" if skills else f"{exp} {edu}".strip()
        return RawJob(
            id=f"lagou-{jid}",
            title=item.get("positionName", ""),
            company=(item.get("company") or {}).get("companyName", ""),
            location=f"{item.get('city', '')} {item.get('district', '')}".strip(),
            url=f"https://www.lagou.com/jobs/{jid}.html",
            description=desc,
            source="lagou",
            salary=salary,
            remote="远程" in item.get("positionName", ""),
            raw_extra=item,
        )
    except Exception as exc:
        logger.warning("拉勾网 parse failed: %s", exc)
        return None
