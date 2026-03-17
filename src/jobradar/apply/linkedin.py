"""LinkedIn Easy Apply applier.

Uses Playwright to submit LinkedIn Easy Apply jobs.
Requires: pip install "openclaw-jobradar[apply]"
          LINKEDIN_COOKIES env var (from browser DevTools)

Scope: Easy Apply only (single-step modal).
Multi-step applications with custom questions are skipped.
"""

from __future__ import annotations

import logging
import os
import random
import time

from .base import ApplyResult, ApplyStatus
from .history import ApplyHistory

logger = logging.getLogger(__name__)


class LinkedInApplier:
    platform = "linkedin"

    def __init__(
        self,
        *,
        daily_limit: int = 25,
        delay_min: float = 4.0,
        delay_max: float = 10.0,
        history: ApplyHistory | None = None,
    ):
        self.daily_limit = daily_limit
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.history = history or ApplyHistory()

    def can_apply(self, job: dict) -> bool:
        url = job.get("url", "")
        if "linkedin.com" not in url:
            return False
        if self.history.already_applied(job["id"]):
            return False
        if self.history.daily_count() >= self.daily_limit:
            return False
        return True

    def apply(self, job: dict, *, dry_run: bool = False) -> ApplyResult:
        base = dict(job_id=job["id"], title=job["title"],
                    company=job.get("company", ""), platform=self.platform)

        if not self.can_apply(job):
            if self.history.already_applied(job["id"]):
                return ApplyResult(**base, status=ApplyStatus.SKIPPED,
                                   message="already applied")
            if self.history.daily_count() >= self.daily_limit:
                return ApplyResult(**base, status=ApplyStatus.SKIPPED,
                                   message=f"daily limit {self.daily_limit} reached")
            return ApplyResult(**base, status=ApplyStatus.SKIPPED, message="not applicable")

        if dry_run:
            return ApplyResult(**base, status=ApplyStatus.DRY_RUN,
                               message="dry-run: would click Easy Apply")

        try:
            result = self._do_apply(job)
            if result.status == ApplyStatus.APPLIED:
                self.history.record(job["id"])
                delay = random.uniform(self.delay_min, self.delay_max)
                time.sleep(delay)
            return result
        except Exception as exc:
            logger.error("LinkedIn apply failed for %s: %s", job["title"], exc)
            return ApplyResult(**base, status=ApplyStatus.FAILED, message=str(exc))

    def _do_apply(self, job: dict) -> ApplyResult:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install 'openclaw-jobradar[apply]' "
                "&& playwright install chromium"
            )

        base = dict(job_id=job["id"], title=job["title"],
                    company=job.get("company", ""), platform=self.platform)

        cookies_str = os.getenv("LINKEDIN_COOKIES", "").strip()
        if not cookies_str:
            return ApplyResult(**base, status=ApplyStatus.BLOCKED,
                               message="LINKEDIN_COOKIES not set")

        pw_cookies = _parse_cookie_string(cookies_str, domain=".linkedin.com")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            )
            ctx.add_cookies(pw_cookies)
            page = ctx.new_page()

            try:
                page.goto(job["url"], wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)

                # Find Easy Apply button (not the regular Apply)
                easy_btn = page.locator(
                    "button.jobs-apply-button:has-text('Easy Apply'), "
                    ".jobs-s-apply button:has-text('Easy Apply')"
                ).first

                if easy_btn.count() == 0:
                    return ApplyResult(**base, status=ApplyStatus.SKIPPED,
                                       message="No Easy Apply button — multi-step or external")

                easy_btn.click(timeout=8000)
                page.wait_for_timeout(1500)

                # Check for multi-step modal (has "Next" button = complex form → skip)
                if page.locator("button[aria-label='Continue to next step']").count() > 0:
                    # Close modal and skip
                    page.locator("button[aria-label='Dismiss']").first.click(timeout=3000)
                    return ApplyResult(**base, status=ApplyStatus.SKIPPED,
                                       message="Multi-step application — skipped")

                # Single-step: click Submit application
                submit = page.locator(
                    "button[aria-label='Submit application'], "
                    "button:has-text('Submit application')"
                ).first

                if submit.count() == 0:
                    return ApplyResult(**base, status=ApplyStatus.FAILED,
                                       message="Submit button not found")

                submit.click(timeout=8000)
                page.wait_for_timeout(1500)

                return ApplyResult(**base, status=ApplyStatus.APPLIED,
                                   message="Easy Apply submitted")

            except PWTimeout as e:
                return ApplyResult(**base, status=ApplyStatus.FAILED,
                                   message=f"Timeout: {e}")
            finally:
                browser.close()

    def close(self) -> None:
        pass


def _parse_cookie_string(cookie_str: str, domain: str) -> list[dict]:
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        name, _, value = part.partition("=")
        cookies.append({"name": name.strip(), "value": value.strip(),
                         "domain": domain, "path": "/"})
    return cookies
