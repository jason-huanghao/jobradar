"""拉勾网 job scraper.

拉勾网 is a major Chinese tech job platform. This implementation uses
the documented API pattern (GET cookies → POST JSON request).

Rate limiting is implemented to avoid being blocked.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from ..config import AppConfig
from ..models import RawJob
from .base import JobSource


logger = logging.getLogger(__name__)


class LagouSource(JobSource):
    """拉勾网 job source implementation."""
    
    name = "lagou"
    
    def __init__(self):
        self._cookie_file = Path("./memory/lagou_cookies.json")
        self._cookies = self._load_cookies()
    
    def is_enabled(self, config: AppConfig) -> bool:
        lagou_config = getattr(config.sources, "lagou", None)
        if lagou_config is None:
            return False
        return getattr(lagou_config, "enabled", False)
    
    def _load_cookies(self) -> dict[str, str]:
        """Load cookies from file if exists."""
        if self._cookie_file.exists():
            try:
                with open(self._cookie_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")
        return {}
    
    def _save_cookies(self, cookies: dict[str, str]) -> None:
        """Save cookies to file."""
        self._cookie_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cookie_file, "w") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        logger.info(f"Cookies saved to {self._cookie_file}")
    
    def _get_cookies(self, config: AppConfig) -> dict[str, str]:
        """Get cookies from 拉勾网 by visiting the site."""
        if not self._cookies:
            logger.info("No cookies found, fetching from 拉勾网...")
            
            try:
                with httpx.Client(follow_redirects=True) as client:
                    # Visit 拉勾网 homepage to get initial cookies
                    response = client.get("https://www.lagou.com/", timeout=30.0)
                    
                    # Extract cookies from response (httpx Cookies is a dict-like)
                    cookies = dict(response.cookies)
                    
                    if cookies:
                        self._cookies = cookies
                        self._save_cookies(cookies)
                        logger.info(f"Got {len(cookies)} cookies from 拉勾网")
            except Exception as e:
                logger.error(f"Failed to fetch cookies: {e}")
        
        return self._cookies
    
    def search(self, query: Any, config: AppConfig) -> list[RawJob]:
        """Search for jobs on 拉勾网.
        
        拉勾网 uses a 2-step process:
        1. GET request to get cookies
        2. POST request with JSON payload to search API
        """
        lagou_config = getattr(config.sources, "lagou", None)
        
        cookies = self._get_cookies(config)
        if not cookies:
            logger.warning("拉勾网: No cookies available, returning empty results")
            return []
        
        city_code = getattr(lagou_config, "city_code", "101020100")
        keyword = query.keyword
        url = "https://www.lagou.com/jobs/v2/positionAjax.json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.lagou.com/jobs/list",
            "Origin": "https://www.lagou.com",
            "Cookie": "; ".join([f"{k}={v}" for k, v in cookies.items()]),
        }
        payload = {"first": "true", "pn": 1, "kd": keyword, "city": city_code,
                   "needAddtionalResult": "false"}
        
        try:
            time.sleep(getattr(lagou_config, "delay_between_requests", 2.0))
            with httpx.Client(follow_redirects=True) as client:
                response = client.post(url, json=payload, headers=headers, timeout=30.0)
            
            if response.status_code != 200:
                logger.error("拉勾网 API error: %s", response.status_code)
                return []
            
            data = response.json()
            if data.get("success") is not True:
                logger.error("拉勾网 API returned error: %s", data.get("msg", "Unknown"))
                return []
            
            content = data.get("content", {}).get("positionResult", {}).get("result", [])
            max_r = getattr(lagou_config, "max_results_per_source", 50)
            jobs: list[RawJob] = []
            for item in content[:max_r]:
                try:
                    jobs.append(self._parse_job(item, query))
                except Exception as e:
                    logger.warning("Failed to parse 拉勾网 job: %s", e)
            
            logger.info("拉勾网: %d jobs for '%s'", len(jobs), keyword)
            return jobs
            
        except httpx.TimeoutException:
            logger.error("拉勾网 request timeout")
            return []
        except Exception as e:
            logger.error("拉勾网 search failed: %s", e, exc_info=True)
            return []
    
    def _parse_job(self, item: dict, query: Any) -> RawJob:
        """Parse job item from 拉勾网 API response."""
        
        job_id = item.get("positionId", "")
        title = item.get("positionName", "")
        company = item.get("company", {}).get("companyName", "")
        
        # Location
        city_name = item.get("city", "")
        district = item.get("district", "")
        location = f"{city_name} {district}".strip()
        
        # Salary
        salary_min = item.get("salaryMin", "")
        salary_max = item.get("salaryMax", "")
        salary_month = item.get("salaryMonth", "")
        
        if salary_min and salary_max:
            salary = f"{salary_min}-{salary_max}K × {salary_month}"
        else:
            salary = item.get("salary", "")
        
        # Work experience requirement
        work_year = item.get("workYear", "")
        experience = work_year.replace("年", " years") if work_year else ""
        
        # Education requirement
        education = item.get("education", "")
        
        # Job URL
        job_url = f"https://www.lagou.com/jobs/{job_id}.html"
        
        # Company size
        company_size = item.get("companySize", "")
        
        # Industry
        industry = item.get("industryField", "")
        
        # Skills
        skills = item.get("skillLables", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        
        # Determine if remote
        remote = "远程" in title or "Remote" in title.lower() or "remote" in title.lower()
        
        # Get raw data for additional metadata
        raw_data = {
            "experience": experience,
            "education": education,
            "company_size": company_size,
            "industry": industry,
            "skills": skills,
        }
        
        return RawJob(
            id=f"lagou-{job_id}",
            title=title,
            company=company,
            location=location,
            source="lagou",
            url=job_url,
            description=f"{title} at {company}. {experience} experience, {education} education.",
            salary=salary,
            remote=remote,
            raw_data=raw_data,
        )
