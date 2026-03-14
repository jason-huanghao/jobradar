"""智联招聘 adapter — no auth required for basic searches."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import httpx

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://fe-api.zhaopin.com/c/i/sou"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36")
_CITY_CODES = {
    "北京": "530", "beijing": "530",
    "上海": "538", "shanghai": "538",
    "深圳": "765", "shenzhen": "765",
    "广州": "763", "guangzhou": "763",
    "杭州": "653", "hangzhou": "653",
    "成都": "801", "chengdu": "801",
    "武汉": "736", "wuhan": "736",
    "南京": "635", "nanjing": "635",
}


class ZhilianSource(JobSource):
    source_id = "zhilian"

    def is_enabled(self, config) -> bool:
        return getattr(config.sources.zhilian, "enabled", False)

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        headers = {"User-Agent": _UA, "Referer": "https://www.zhaopin.com/", "Accept": "application/json"}
        all_jobs: list[RawJob] = []
        seen: set[str] = set()

        for query in queries:
            city_code = _CITY_CODES.get(query.location.lower(), "538")
            max_results = query.extra.get("max_results", 50)
            page, page_size = 1, min(20, max_results)

            with httpx.Client(timeout=20.0) as client:
                while len(all_jobs) < max_results:
                    time.sleep(1.0)
                    try:
                        resp = client.get(_SEARCH_URL, params={
                            "kw": query.keyword, "cityId": city_code,
                            "pageSize": page_size, "pageNum": page,
                            "salary": "0,0", "workExperience": "-1",
                            "education": "-1", "jobType": "2",
                        }, headers=headers)
                        resp.raise_for_status()
                        results = resp.json().get("data", {}).get("results", [])
                    except Exception as exc:
                        logger.error("智联招聘 error: %s", exc)
                        break
                    if not results:
                        break
                    for item in results:
                        job = _parse(item)
                        if job and job.id not in seen:
                            seen.add(job.id)
                            all_jobs.append(job)
                    if len(results) < page_size:
                        break
                    page += 1

        return all_jobs


def _parse(item: dict) -> RawJob | None:
    try:
        jid = str(item.get("number", item.get("positionId", "")))
        city = (item.get("city") or {}).get("display", "")
        area = ((item.get("workingAddresses") or [{}])[0]).get("areaDistrict", "")
        sal = item.get("salaryReal", {})
        salary = f"{sal.get('low', 0)}–{sal.get('high', 0)}K" if sal.get("low") else ""
        welfare = item.get("welfare", "")
        skills = item.get("skillLables", [])
        desc = welfare or "；".join(skills)
        return RawJob(
            id=f"zhilian-{jid}",
            title=item.get("jobName", ""),
            company=(item.get("company") or {}).get("name", ""),
            location=f"{city} {area}".strip(),
            url=f"https://jobs.zhaopin.com/{jid}.htm",
            description=desc,
            source="zhilian",
            date_posted=item.get("updateDate", ""),
            salary=salary,
            raw_extra=item,
        )
    except Exception as exc:
        logger.warning("智联招聘 parse failed: %s", exc)
        return None
