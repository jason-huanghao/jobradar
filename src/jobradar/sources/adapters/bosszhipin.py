"""BOSS直聘 adapter — cookie-based JSON API + Playwright cookie capture.

Setup (one-time, three options):
  A) python -m jobradar.sources.adapters.bosszhipin --capture-cookies  (recommended)
  B) export BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"
  C) ./memory/bosszhipin_cookies.json  {"__zp_stoken__":"xxx","wt2":"yyy"}

Cookies expire in ~7 days — re-run --capture-cookies to refresh.
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from datetime import datetime
from pathlib import Path

import httpx

from ...models.job import RawJob, SearchQuery
from ..base import JobSource

logger = logging.getLogger(__name__)

_SEARCH_URL      = "https://www.zhipin.com/wapi/zpgeek/search/joblist.json"
_REQUIRED_COOKIES = {"__zp_stoken__", "wt2"}
_COOKIE_FILE     = Path("./memory/bosszhipin_cookies.json")
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


class BossZhipinSource(JobSource):
    source_id = "bosszhipin"

    def __init__(self) -> None:
        self._cookie_file = _COOKIE_FILE

    def is_enabled(self, config) -> bool:
        return getattr(config.sources.bosszhipin, "enabled", False)

    def fetch(self, queries: list[SearchQuery], since: datetime) -> list[RawJob]:
        cookies = self._load_cookies()
        if not self._validate_cookies(cookies):
            logger.warning(
                "BOSS直聘: valid cookies not found (need: %s). "
                "Run: python -m jobradar.sources.adapters.bosszhipin --capture-cookies",
                _REQUIRED_COOKIES,
            )
            return []
        all_jobs: list[RawJob] = []
        seen: set[str] = set()
        for query in queries:
            jobs = self._search(query, cookies)
            for j in jobs:
                if j.id not in seen:
                    seen.add(j.id)
                    all_jobs.append(j)
        return all_jobs

    def _search(self, query: SearchQuery, cookies: dict) -> list[RawJob]:
        max_results = query.extra.get("max_results", 50)
        delay       = query.extra.get("delay_between_requests", 2.0)
        city_code   = query.extra.get("city_code", "101020100")
        headers = {
            "User-Agent": _UA,
            "Referer": "https://www.zhipin.com/web/geek/job",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
        }
        params: dict = {"scene": 1, "query": query.keyword, "city": city_code,
                        "pageSize": min(30, max_results), "pageIndex": 1}
        jobs: list[RawJob] = []
        with httpx.Client(timeout=20.0) as client:
            while len(jobs) < max_results:
                time.sleep(delay + random.uniform(0.0, 1.0))
                try:
                    resp = client.get(_SEARCH_URL, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.error("BOSS直聘 request failed: %s", e)
                    break
                code = data.get("code")
                if code == 37:
                    logger.warning("BOSS直聘: code 37 — cookies expired. Re-run --capture-cookies.")
                    break
                if code != 0:
                    logger.warning("BOSS直聘 API error code=%s", code)
                    break
                job_list = (data.get("zpData") or {}).get("jobList", [])
                if not job_list:
                    break
                for item in job_list:
                    j = _parse_job(item)
                    if j:
                        jobs.append(j)
                if len(job_list) < params["pageSize"]:
                    break
                params["pageIndex"] += 1
        logger.info("BOSS直聘: %d jobs for '%s'", len(jobs), query.keyword)
        return jobs[:max_results]

    def _load_cookies(self) -> dict[str, str]:
        env = os.getenv("BOSSZHIPIN_COOKIES", "").strip()
        if env:
            parsed: dict[str, str] = {}
            for part in env.split(";"):
                if "=" in part:
                    k, _, v = part.strip().partition("=")
                    parsed[k.strip()] = v.strip()
            if parsed:
                return parsed
        if self._cookie_file.exists():
            try:
                data = json.loads(self._cookie_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception as e:
                logger.warning("Failed to load BOSS直聘 cookies: %s", e)
        return {}

    def _validate_cookies(self, cookies: dict) -> bool:
        return all(cookies.get(k) for k in _REQUIRED_COOKIES)

    def capture_cookies_with_playwright(self) -> dict[str, str]:
        """Open a visible browser for manual login, capture and save cookies."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return {}
        logger.info("Opening browser for BOSS直聘 login — please log in within 2 minutes…")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False,
                args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(user_agent=_UA, viewport={"width": 1280, "height": 800},
                                      locale="zh-CN")
            ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
            page = ctx.new_page()
            page.goto("https://www.zhipin.com/web/user/?ka=header-login",
                      wait_until="domcontentloaded")
            try:
                page.wait_for_url("**/web/geek/**", timeout=180_000)
                logger.info("Login detected — capturing cookies…")
            except Exception:
                logger.warning("Login timeout — capturing whatever cookies exist…")
            raw_cookies = ctx.cookies()
            browser.close()
        cookies = {c["name"]: c["value"] for c in raw_cookies}
        if not self._validate_cookies(cookies):
            logger.warning("Required cookies not found. Got: %s", set(cookies.keys()))
            return cookies
        self._cookie_file.parent.mkdir(parents=True, exist_ok=True)
        self._cookie_file.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))
        logger.info("Cookies saved to %s", self._cookie_file)
        return cookies


def _parse_job(item: dict) -> RawJob | None:
    try:
        job_id  = item.get("encryptJobId", "")
        title   = item.get("jobName", "").strip()
        if not title:
            return None
        company  = item.get("brandName", "").strip()
        loc_parts = filter(None, [item.get("cityName", ""),
                                   item.get("areaDistrict", ""),
                                   item.get("businessDistrict", "")])
        location = ", ".join(loc_parts)
        salary   = item.get("salaryDesc", "")
        url      = f"https://www.zhipin.com/job_detail/{job_id}.html"
        desc_parts = [s for s in (item.get("jobLabels", []) + item.get("skills", []))
                      if isinstance(s, str)]
        description = "；".join(desc_parts) if desc_parts else ""
        return RawJob(
            id=f"bosszhipin-{job_id}", title=title, company=company, location=location,
            url=url, description=description, source="bosszhipin",
            job_type="fulltime", salary=salary, raw_extra=item,
        )
    except Exception as e:
        logger.warning("Failed to parse BOSS直聘 job: %s", e)
        return None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if "--capture-cookies" in sys.argv:
        src = BossZhipinSource()
        captured = src.capture_cookies_with_playwright()
        if captured:
            print(f"✅ Captured {len(captured)} cookies → {_COOKIE_FILE}")
        else:
            print("❌ Failed to capture cookies")
    else:
        print("Usage: python -m jobradar.sources.adapters.bosszhipin --capture-cookies")
