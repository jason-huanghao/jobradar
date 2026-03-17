"""Boss直聘 auto-greet applier.

Uses Playwright to simulate the 立即沟通 (chat now) flow.
Requires: pip install "openclaw-jobradar[apply]"
          BOSSZHIPIN_COOKIES env var (capture with --capture-cookies)

Anti-ban strategy (mirrors jobclaw):
  - Random delay 3–8 s between applications
  - Hard daily cap (default 50)
  - Skip jobs where HR has been inactive > 7 days
  - Dedup via ApplyHistory (never re-apply same job_id)
"""

from __future__ import annotations

import logging
import os
import random
import time

from .base import ApplyResult, ApplyStatus
from .history import ApplyHistory

logger = logging.getLogger(__name__)

_DEFAULT_GREETING = (
    "您好！我对贵公司的该职位非常感兴趣，"
    "我有相关的技术背景和项目经验，方便进一步沟通吗？"
)


class BossZhipinApplier:
    platform = "bosszhipin"

    def __init__(
        self,
        *,
        greeting_template: str = "",
        daily_limit: int = 50,
        delay_min: float = 3.0,
        delay_max: float = 8.0,
        inactive_days_skip: int = 7,
        history: ApplyHistory | None = None,
    ):
        self.greeting_template = greeting_template or _DEFAULT_GREETING
        self.daily_limit = daily_limit
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.inactive_days_skip = inactive_days_skip
        self.history = history or ApplyHistory()
        self._browser = None
        self._page = None

    def can_apply(self, job: dict) -> bool:
        if not job.get("url", "").startswith("https://www.zhipin.com"):
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
                               message="dry-run: would send greeting")

        try:
            result = self._do_apply(job)
            if result.status == ApplyStatus.APPLIED:
                self.history.record(job["id"])
                delay = random.uniform(self.delay_min, self.delay_max)
                logger.debug("Applied to %s, waiting %.1fs", job["title"], delay)
                time.sleep(delay)
            return result
        except Exception as exc:
            logger.error("Boss直聘 apply failed for %s: %s", job["title"], exc)
            return ApplyResult(**base, status=ApplyStatus.FAILED, message=str(exc))

    def _do_apply(self, job: dict) -> ApplyResult:
        """Playwright automation — opens job page and clicks 立即沟通."""
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install 'openclaw-jobradar[apply]' "
                "&& playwright install chromium"
            )

        base = dict(job_id=job["id"], title=job["title"],
                    company=job.get("company", ""), platform=self.platform)

        cookies_str = os.getenv("BOSSZHIPIN_COOKIES", "").strip()
        if not cookies_str:
            return ApplyResult(**base, status=ApplyStatus.BLOCKED,
                               message="BOSSZHIPIN_COOKIES not set")

        pw_cookies = _parse_cookie_string(cookies_str, domain=".zhipin.com")

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

                # Check HR activity
                try:
                    active_txt = page.locator(".boss-active-time").inner_text(timeout=3000)
                    if _is_inactive_hr(active_txt, self.inactive_days_skip):
                        return ApplyResult(**base, status=ApplyStatus.BLOCKED,
                                           message=f"HR inactive: {active_txt}")
                except PWTimeout:
                    pass  # no activity indicator — continue

                # Check for CAPTCHA
                if page.locator(".verify-wrap").count() > 0:
                    return ApplyResult(**base, status=ApplyStatus.BLOCKED,
                                       message="CAPTCHA detected — manual intervention needed")

                # Click 立即沟通
                btn = page.locator("a.btn-startchat, .btn-primary:has-text('立即沟通')").first
                btn.click(timeout=8000)
                page.wait_for_timeout(1500)

                # Type greeting in chat input
                chat_input = page.locator(".chat-input-box textarea, .chat-input textarea").first
                greeting = _format_greeting(self.greeting_template, job)
                chat_input.fill(greeting)
                page.wait_for_timeout(500)

                # Send
                send_btn = page.locator(".btn-send, button:has-text('发送')").first
                send_btn.click(timeout=5000)
                page.wait_for_timeout(1000)

                return ApplyResult(**base, status=ApplyStatus.APPLIED,
                                   message=f"Greeting sent: {greeting[:60]}…")

            except PWTimeout as e:
                return ApplyResult(**base, status=ApplyStatus.FAILED,
                                   message=f"Timeout: {e}")
            finally:
                browser.close()

    def close(self) -> None:
        pass  # stateless — Playwright context opened/closed per apply()

# ── Helpers ────────────────────────────────────────────────────────

def _parse_cookie_string(cookie_str: str, domain: str) -> list[dict]:
    """Parse 'name=value; name2=value2' into Playwright cookie dicts."""
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        name, _, value = part.partition("=")
        cookies.append({
            "name": name.strip(),
            "value": value.strip(),
            "domain": domain,
            "path": "/",
        })
    return cookies


def _is_inactive_hr(active_text: str, threshold_days: int) -> bool:
    """Return True if HR text implies inactivity beyond threshold."""
    import re
    # e.g. "3天前活跃", "1个月前活跃", "半年前活跃"
    month_match = re.search(r'(\d+)\s*个月', active_text)
    if month_match and int(month_match.group(1)) * 30 > threshold_days:
        return True
    if "半年" in active_text or "一年" in active_text:
        return True
    day_match = re.search(r'(\d+)\s*天', active_text)
    if day_match and int(day_match.group(1)) > threshold_days:
        return True
    return False


def _format_greeting(template: str, job: dict) -> str:
    """Replace $title, $company placeholders in greeting template."""
    return (template
            .replace("$title", job.get("title", "该职位"))
            .replace("$company", job.get("company", "贵公司")))
