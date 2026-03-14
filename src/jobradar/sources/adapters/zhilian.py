"""智联招聘 adapter — REST API primary, Playwright XHR-intercept fallback.

Strategy 1 (primary):  fe-api.zhaopin.com REST endpoint — no auth, paginated, fast.
Strategy 2 (fallback): Playwright stealth + XHR interception + DOM parse.
"""
from __future__ import annotations

import logging
import random
import time
from datetime import datetime
from urllib.parse import quote

import httpx

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_CITY_CODES: dict[str, str] = {
    "北京": "530",  "beijing": "530",
    "上海": "538",  "shanghai": "538",
    "深圳": "765",  "shenzhen": "765",
    "广州": "763",  "guangzhou": "763",
    "杭州": "653",  "hangzhou": "653",
    "成都": "801",  "chengdu": "801",
    "武汉": "736",  "wuhan": "736",
    "南京": "635",  "nanjing": "635",
    "西安": "703",  "xian": "703",
}
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_SOU_API = "https://fe-api.zhaopin.com/c/i/sou"
_API_HEADERS = {
    "User-Agent": _UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://sou.zhaopin.com/",
}


class ZhilianSource(JobSource):
    source_id = "zhilian"

    def is_enabled(self, config) -> bool:
        return getattr(config.sources.zhilian, "enabled", False)

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
        city_code   = _CITY_CODES.get(query.location.lower(), "538")
        keyword     = query.keyword

        jobs = self._rest_api(keyword, city_code, max_results)
        if jobs:
            logger.info("智联招聘 [REST]: %d jobs for '%s'", len(jobs), keyword)
            return jobs

        jobs = self._playwright(keyword, city_code, max_results)
        logger.info("智联招聘 [Playwright]: %d jobs for '%s'", len(jobs), keyword)
        return jobs

    def _rest_api(self, keyword: str, city_code: str, max_results: int) -> list[RawJob]:
        jobs: list[RawJob] = []
        page, page_size = 1, min(90, max_results)
        try:
            with httpx.Client(timeout=20.0) as client:
                while len(jobs) < max_results:
                    resp = client.get(_SOU_API, headers=_API_HEADERS, params={
                        "jl": city_code, "kw": keyword,
                        "p": page, "pageSize": page_size, "sortType": "publish",
                    })
                    resp.raise_for_status()
                    data = resp.json()
                    results = (data.get("data") or {}).get("results", [])
                    if not results:
                        break
                    for item in results:
                        j = _parse_api_item(item)
                        if j:
                            jobs.append(j)
                    num_found = (data.get("data") or {}).get("numFound", 0)
                    if len(jobs) >= num_found or len(jobs) >= max_results:
                        break
                    page += 1
                    time.sleep(random.uniform(0.5, 1.2))
        except Exception as e:
            logger.warning("智联招聘 REST API failed: %s", e)
        return jobs[:max_results]

    def _playwright(self, keyword: str, city_code: str, max_results: int) -> list[RawJob]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright not installed — skipping 智联招聘 fallback")
            return []
        jobs: list[RawJob] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled",
                          "--disable-dev-shm-usage", "--no-sandbox"],
                )
                ctx = browser.new_context(
                    user_agent=_UA, viewport={"width": 1366, "height": 768},
                    locale="zh-CN", timezone_id="Asia/Shanghai",
                    extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
                )
                ctx.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                    "window.chrome={runtime:{}};"
                    "Object.defineProperty(navigator,'languages',{get:()=>['zh-CN','zh','en']});"
                )
                page = ctx.new_page()
                xhr_data: list[dict] = []
                def _on_resp(response):
                    try:
                        if "fe-api.zhaopin.com" in response.url:
                            xhr_data.append(response.json())
                    except Exception:
                        pass
                page.on("response", _on_resp)

                page.goto(f"https://sou.zhaopin.com/?jl={city_code}&kw={quote(keyword)}&p=1",
                          wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(random.randint(2000, 3500))

                for xhr in xhr_data:
                    for item in (xhr.get("data") or {}).get("results", []):
                        j = _parse_api_item(item)
                        if j:
                            jobs.append(j)

                # Paginate if needed
                page_no = 2
                while len(jobs) < max_results and page_no <= 5:
                    xhr_data.clear()
                    page.goto(
                        f"https://sou.zhaopin.com/?jl={city_code}&kw={quote(keyword)}&p={page_no}",
                        wait_until="networkidle", timeout=45000)
                    page.wait_for_timeout(random.randint(1500, 2500))
                    for xhr in xhr_data:
                        results = (xhr.get("data") or {}).get("results", [])
                        if not results:
                            break
                        for item in results:
                            j = _parse_api_item(item)
                            if j:
                                jobs.append(j)
                    if not xhr_data:
                        break
                    page_no += 1

                # DOM fallback
                if not jobs:
                    try:
                        page.wait_for_selector(".joblist-box__item", timeout=10000)
                    except Exception:
                        pass
                    raw = page.evaluate("""() => {
                        const out = [];
                        document.querySelectorAll('.joblist-box__item').forEach(el => {
                            const t = el.querySelector('.jobinfo__name,a[href*="/jobs/"]');
                            const c = el.querySelector('.companyinfo__name');
                            const l = el.querySelector('.jobinfo__add');
                            const s = el.querySelector('.jobinfo__salary');
                            const a = el.querySelector('a[href*="/jobs/"]');
                            if (t) out.push({title:t.textContent?.trim()||'',
                                company:c?.textContent?.trim()||'',
                                location:l?.textContent?.trim()||'',
                                salary:s?.textContent?.trim()||'',
                                url:a?.href||''});
                        });
                        return out;
                    }""")
                    for i, item in enumerate(raw[:max_results]):
                        if item.get("title"):
                            jobs.append(RawJob(
                                id=f"zhilian-pw-{i}-{abs(hash(item.get('url','')))%10**7}",
                                title=item["title"], company=item.get("company", ""),
                                location=item.get("location", ""),
                                url=item.get("url") or "https://sou.zhaopin.com",
                                description=f"薪资: {item.get('salary','N/A')}",
                                source="zhilian", salary=item.get("salary", ""),
                            ))
                browser.close()
        except Exception as e:
            logger.error("智联招聘 Playwright failed: %s", e, exc_info=True)
        return jobs[:max_results]


def _parse_api_item(item: dict) -> RawJob | None:
    try:
        job_id = str(item.get("number", item.get("positionId", "")))
        title  = (item.get("name") or item.get("jobName", "")).strip()
        if not title:
            return None
        company_obj = item.get("company") or {}
        company = (company_obj.get("name") or item.get("companyName", "")).strip()
        loc_parts = []
        city = item.get("city") or {}
        loc_parts.append(city.get("name", "") if isinstance(city, dict) else str(city))
        district = item.get("district") or {}
        if isinstance(district, dict) and district.get("name"):
            loc_parts.append(district["name"])
        location = "·".join(p for p in loc_parts if p)
        sal = item.get("salary60", {})
        salary = (f"{sal.get('from',0)}-{sal.get('to',0)}K/月"
                  if sal.get("from") or sal.get("to")
                  else item.get("salaryReal", "") or "")
        url = f"https://jobs.zhaopin.com/{job_id}.htm" if job_id else "https://www.zhaopin.com"
        welfare = item.get("welfare", [])
        skills  = item.get("skills", [])
        tags = (welfare if isinstance(welfare, list) else []) + \
               (skills  if isinstance(skills,  list) else [])
        description = "；".join(str(t) for t in tags) if tags else item.get("jobSummary", "")
        return RawJob(
            id=f"zhilian-{job_id}", title=title, company=company, location=location,
            url=url, description=description, source="zhilian", salary=salary,
            date_posted=item.get("updateDate", item.get("createDate", "")),
            raw_extra=item,
        )
    except Exception as e:
        logger.warning("Failed to parse Zhilian item: %s", e)
        return None
