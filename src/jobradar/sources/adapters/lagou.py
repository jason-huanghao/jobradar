"""拉勾网 adapter — 3-strategy cascade to defeat CAPTCHA.

Strategy 1 (primary):   Mobile JSON API — zero CAPTCHA, fast.
Strategy 2 (secondary): Desktop AJAX + session warm-up.
Strategy 3 (fallback):  Playwright stealth + XHR interception.
"""
from __future__ import annotations

import logging
import random
import time
from datetime import datetime

import httpx

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_CITY_MAP: dict[str, str] = {
    "上海": "上海", "shanghai": "上海", "北京": "北京", "beijing": "北京",
    "广州": "广州", "guangzhou": "广州", "深圳": "深圳", "shenzhen": "深圳",
    "杭州": "杭州", "hangzhou": "杭州", "成都": "成都", "chengdu": "成都",
    "武汉": "武汉", "wuhan": "武汉",   "南京": "南京", "nanjing": "南京",
    "西安": "西安", "xian": "西安",
}
_MOBILE_API  = "https://m.lagou.com/search.json"
_AJAX_API    = "https://www.lagou.com/jobs/positionAjax.json"
_UA_MOBILE   = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
_UA_DESKTOP  = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_MOBILE_HEADERS = {
    "User-Agent": _UA_MOBILE, "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://m.lagou.com/", "Accept-Language": "zh-CN,zh;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}
_AJAX_HEADERS = {
    "User-Agent": _UA_DESKTOP, "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded", "Origin": "https://www.lagou.com",
}


class LagouSource(JobSource):
    source_id = "lagou"

    def is_enabled(self, config) -> bool:
        return getattr(config.sources.lagou, "enabled", False)

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
        city    = _CITY_MAP.get(query.location.lower(), query.location or "上海")
        keyword = query.keyword

        jobs = self._mobile_api(keyword, city, max_results)
        if jobs:
            logger.info("拉勾网 [mobile]: %d jobs for '%s'", len(jobs), keyword)
            return jobs

        jobs = self._ajax_api(keyword, city, max_results)
        if jobs:
            logger.info("拉勾网 [AJAX]: %d jobs for '%s'", len(jobs), keyword)
            return jobs

        jobs = self._playwright(keyword, city, max_results)
        logger.info("拉勾网 [Playwright]: %d jobs for '%s'", len(jobs), keyword)
        return jobs

    def _mobile_api(self, keyword: str, city: str, max_results: int) -> list[RawJob]:
        jobs: list[RawJob] = []
        page_no, page_size = 1, min(15, max_results)
        try:
            with httpx.Client(timeout=20.0) as client:
                while len(jobs) < max_results:
                    resp = client.get(_MOBILE_API, headers=_MOBILE_HEADERS, params={
                        "kd": keyword, "city": city,
                        "pageNo": page_no, "pageSize": page_size,
                    })
                    resp.raise_for_status()
                    data = resp.json()
                    page_obj = (data.get("content") or {}).get("data", {}).get("page", {})
                    items = page_obj.get("result", [])
                    if not items:
                        break
                    for item in items:
                        j = _parse_item(item)
                        if j:
                            jobs.append(j)
                    total = page_obj.get("totalCount", 0)
                    if len(jobs) >= total or len(jobs) >= max_results:
                        break
                    page_no += 1
                    time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logger.warning("拉勾网 mobile API failed: %s", e)
        return jobs[:max_results]

    def _ajax_api(self, keyword: str, city: str, max_results: int) -> list[RawJob]:
        jobs: list[RawJob] = []
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                client.get("https://www.lagou.com",
                           headers={"User-Agent": _UA_DESKTOP, "Accept": "text/html"})
                time.sleep(random.uniform(1.0, 2.0))
                referer = f"https://www.lagou.com/jobs/list_{keyword}?city={city}&cl=false&fromSearch=true"
                page = 1
                while len(jobs) < max_results:
                    resp = client.post(
                        _AJAX_API,
                        headers={**_AJAX_HEADERS, "Referer": referer},
                        params={"needAddtionalResult": "false", "isSchoolJob": "0"},
                        data={"first": "true" if page == 1 else "false",
                              "pn": str(page), "kd": keyword, "city": city},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("status") != 0:
                        break
                    pos_result = (data.get("content") or {}).get("positionResult", {})
                    items = pos_result.get("result", [])
                    if not items:
                        break
                    for item in items:
                        j = _parse_item(item)
                        if j:
                            jobs.append(j)
                    total = pos_result.get("totalCount", 0)
                    if len(jobs) >= total or len(jobs) >= max_results:
                        break
                    page += 1
                    time.sleep(random.uniform(1.2, 2.5))
        except Exception as e:
            logger.warning("拉勾网 AJAX failed: %s", e)
        return jobs[:max_results]

    def _playwright(self, keyword: str, city: str, max_results: int) -> list[RawJob]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright not installed — skipping 拉勾网 fallback")
            return []
        jobs: list[RawJob] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True,
                    args=["--disable-blink-features=AutomationControlled",
                          "--disable-dev-shm-usage", "--no-sandbox"])
                ctx = browser.new_context(user_agent=_UA_DESKTOP,
                    viewport={"width": 1366, "height": 768}, locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"})
                ctx.add_init_script("""
                    Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
                    window.chrome={runtime:{}};
                    Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
                    Object.defineProperty(navigator,'languages',{get:()=>['zh-CN','zh','en']});
                """)
                page = ctx.new_page()
                xhr_jobs: list[dict] = []
                def _on_response(response):
                    if "positionAjax" in response.url or "search.json" in response.url:
                        try:
                            xhr_jobs.append(response.json())
                        except Exception:
                            pass
                page.on("response", _on_response)
                page.goto("https://www.lagou.com", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(random.randint(1200, 2500))
                page.goto(f"https://www.lagou.com/jobs/list_{keyword}"
                          f"?city={city}&cl=false&fromSearch=true",
                          wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(random.randint(2000, 3500))
                if "验证" in page.title() or "captcha" in page.content().lower():
                    logger.warning("拉勾网: CAPTCHA detected, aborting")
                    browser.close()
                    return []
                for xhr in xhr_jobs:
                    for item in (xhr.get("content") or {}).get("positionResult", {}).get("result", []):
                        j = _parse_item(item)
                        if j:
                            jobs.append(j)
                if not jobs:
                    try:
                        page.wait_for_selector(".con_list_item,[data-positionid]", timeout=8000)
                    except Exception:
                        pass
                    raw = page.evaluate("""() => {
                        const out = [];
                        document.querySelectorAll('.con_list_item,[data-positionid]').forEach(el => {
                            const t = el.querySelector('.position_link h3,.job-title');
                            const c = el.querySelector('.company_name a,.company-name');
                            const l = el.querySelector('.work_addr,.job-area');
                            const s = el.querySelector('.money,.salary');
                            const a = el.querySelector('a.position_link,a[href*="/jobs/"]');
                            if (t) out.push({title:t.textContent?.trim()||'',
                                company:c?.textContent?.trim()||'',
                                location:l?.textContent?.trim()||'',
                                salary:s?.textContent?.trim()||'', url:a?.href||''});
                        });
                        return out;
                    }""")
                    for i, item in enumerate(raw[:max_results]):
                        if item.get("title"):
                            jobs.append(RawJob(
                                id=f"lagou-pw-{i}-{abs(hash(item.get('url','')))%10**7}",
                                title=item["title"], company=item.get("company",""),
                                location=item.get("location",""),
                                url=item.get("url") or "https://www.lagou.com",
                                description=f"薪资: {item.get('salary','N/A')}",
                                source="lagou", salary=item.get("salary",""),
                            ))
                browser.close()
        except Exception as e:
            logger.error("拉勾网 Playwright failed: %s", e, exc_info=True)
        return jobs[:max_results]


def _parse_item(item: dict) -> RawJob | None:
    try:
        pos_id = str(item.get("positionId", ""))
        title  = item.get("positionName", "").strip()
        if not title:
            return None
        company  = (item.get("companyFullName") or item.get("companyShortName") or "").strip()
        city, dist = item.get("city", ""), item.get("district", "")
        location = f"{city}·{dist}" if dist else city
        salary   = item.get("salary", "")
        url      = f"https://www.lagou.com/jobs/{pos_id}.html" if pos_id else "https://www.lagou.com"
        tags     = item.get("skillLables") or item.get("labels") or []
        tag_str  = ", ".join(tags) if isinstance(tags, list) else ""
        description = f"薪资: {salary}" + (f" | 技能: {tag_str}" if tag_str else "")
        return RawJob(
            id=f"lagou-{pos_id}", title=title, company=company, location=location,
            url=url, description=description, source="lagou", salary=salary, raw_extra=item,
        )
    except Exception as e:
        logger.warning("Failed to parse Lagou item: %s", e)
        return None
