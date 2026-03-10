"""智联招聘 (Zhaopin / Zhilian) job source adapter.

智联招聘 (zhaopin.com) is one of China's largest job boards with ~200 M registered users.
It works well for AI/ML roles in Beijing, Shanghai, Shenzhen.

This adapter calls their public search API (no auth required for basic searches).
API: https://fe-api.zhaopin.com/c/i/sou
"""

from __future__ import annotations

import logging
import time

import httpx

from ..config import AppConfig
from ..models import RawJob, SearchQuery
from .base import JobSource

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://fe-api.zhaopin.com/c/i/sou"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Zhilian city codes (different from BOSS直聘)
_CITY_CODES: dict[str, str] = {
    "北京": "530",  "beijing":  "530",
    "上海": "538",  "shanghai": "538",
    "深圳": "765",  "shenzhen": "765",
    "广州": "763",  "guangzhou":"763",
    "杭州": "653",  "hangzhou": "653",
    "成都": "801",  "chengdu":  "801",
    "武汉": "736",  "wuhan":    "736",
    "南京": "635",  "nanjing":  "635",
}


class ZhilianSource(JobSource):
    """智联招聘 job source."""

    name = "zhilian"

    def is_enabled(self, config: AppConfig) -> bool:
        zhilian = getattr(config.sources, "zhilian", None)
        return bool(zhilian and getattr(zhilian, "enabled", False))

    def search(self, query: SearchQuery, config: AppConfig) -> list[RawJob]:
        max_results = query.extra.get("max_results", config.search.max_results_per_source)
        city_code = _CITY_CODES.get(query.location.lower(), "538")  # default Shanghai

        headers = {
            "User-Agent": _USER_AGENT,
            "Referer": "https://www.zhaopin.com/",
            "Accept": "application/json",
        }

        jobs: list[RawJob] = []
        page = 1
        page_size = min(20, max_results)

        with httpx.Client(timeout=20.0) as client:
            while len(jobs) < max_results:
                params = {
                    "kw": query.keyword,
                    "cityId": city_code,
                    "pageSize": page_size,
                    "pageNum": page,
                    "salary": "0,0",       # 0,0 = all salaries
                    "workExperience": "-1", # -1 = any experience
                    "education": "-1",      # -1 = any education
                    "companyType": "-1",
                    "industryType": "0",
                    "jobType": "2",        # 2 = full-time
                }
                try:
                    time.sleep(1.0)
                    resp = client.get(_SEARCH_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.error("智联招聘 search failed: %s", e)
                    break

                results = data.get("data", {}).get("results", [])
                if not results:
                    break

                for item in results:
                    job = _parse_job(item)
                    if job:
                        jobs.append(job)

                if len(results) < page_size:
                    break
                page += 1

        logger.info("智联招聘: %d jobs for '%s' in '%s'",
                    len(jobs), query.keyword, query.location)
        return jobs[:max_results]


def _parse_job(item: dict) -> RawJob | None:
    try:
        job_id = str(item.get("number", item.get("positionId", "")))
        title = item.get("jobName", "")
        company = (item.get("company") or {}).get("name", "")
        city = (item.get("city") or {}).get("display", "")
        area = (item.get("workingAddresses") or [{}])[0].get("areaDistrict", "")
        location = f"{city} {area}".strip()

        salary_low = item.get("salaryReal", {}).get("low", 0)
        salary_high = item.get("salaryReal", {}).get("high", 0)
        salary_month = item.get("salaryReal", {}).get("period", "")
        salary = f"{salary_low}–{salary_high}K/{salary_month}" if salary_low else ""

        url = f"https://jobs.zhaopin.com/{job_id}.htm"
        description = item.get("welfare", "")
        if not description:
            skills = item.get("skillLables", [])
            description = "；".join(skills) if skills else ""

        return RawJob(
            id=f"zhilian-{job_id}",
            title=title,
            company=company,
            location=location,
            url=url,
            description=description,
            source="zhilian",
            date_posted=item.get("updateDate", ""),
            job_type="fulltime",
            salary=salary,
            raw_data=item,
        )
    except Exception as e:
        logger.warning("Failed to parse 智联招聘 job: %s", e)
        return None
