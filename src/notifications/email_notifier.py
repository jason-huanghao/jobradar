"""Email notifier — send digest email after daily update.

Uses Python's built-in smtplib. No external dependencies.
Supports Gmail App Passwords, Outlook, and generic SMTP.
"""

from __future__ import annotations

import logging
import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from ..models import ScoredJob

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send daily job digest emails via SMTP."""

    def __init__(self, cfg: dict) -> None:
        """cfg = config.notifications.email dict."""
        self.enabled: bool = cfg.get("enabled", False)
        self.smtp_host: str = cfg.get("smtp_host", "smtp.gmail.com")
        self.smtp_port: int = cfg.get("smtp_port", 587)
        self.from_addr: str = cfg.get("from_addr", "")
        self.to_addr: str = cfg.get("to_addr", "")
        self.app_password_env: str = cfg.get("app_password_env", "GMAIL_APP_PASSWORD")
        self.min_score: float = float(cfg.get("min_score_to_notify", 7))
        self.max_jobs: int = int(cfg.get("max_jobs_in_email", 10))

    @property
    def password(self) -> str:
        return os.getenv(self.app_password_env, "")

    def send_digest(self, new_jobs: list[ScoredJob], total_scanned: int) -> bool:
        """Send digest email for new high-score jobs. Returns True if sent."""
        if not self.enabled:
            return False

        qualifying = [j for j in new_jobs if j.score >= self.min_score]
        if not qualifying:
            logger.info("Email: no new jobs scored >= %.1f, skipping", self.min_score)
            return False

        if not self.password:
            logger.warning(
                "Email enabled but %s not set in environment — skipping",
                self.app_password_env,
            )
            return False

        qualifying.sort(key=lambda s: s.score, reverse=True)
        top = qualifying[: self.max_jobs]

        subject = (
            f"🎯 {len(qualifying)} new job match{'es' if len(qualifying) > 1 else ''} "
            f"today — top score {top[0].score:.1f}/10"
        )

        html = _build_html(top, qualifying, total_scanned, self.min_score)
        text = _build_text(top, qualifying, total_scanned, self.min_score)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = self.to_addr
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.from_addr, self.password)
                server.sendmail(self.from_addr, self.to_addr, msg.as_string())

            logger.info("Email sent: %d jobs to %s", len(top), self.to_addr)
            return True

        except Exception as e:
            logger.error("Email send failed: %s", e)
            return False


# ── HTML + plain text builders ─────────────────────────────────────

def _build_html(
    jobs: list[ScoredJob],
    all_qualifying: list[ScoredJob],
    total: int,
    min_score: float,
) -> str:
    today = date.today().isoformat()
    rows = ""
    for sj in jobs:
        score_color = "#27AE60" if sj.score >= 8 else "#F39C12" if sj.score >= 6 else "#E74C3C"
        remote = " 🏠" if sj.job.remote else ""
        rows += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #eee;">
            <strong><a href="{sj.job.url}" style="color:#2C3E50;text-decoration:none;">
              {sj.job.title}</a></strong><br>
            <span style="color:#666;">{sj.job.company} · {sj.job.location}{remote}</span><br>
            <small style="color:#999;">{sj.job.source} · {sj.job.date_posted}</small>
          </td>
          <td style="padding:10px;border-bottom:1px solid #eee;text-align:center;">
            <span style="background:{score_color};color:white;padding:4px 10px;
              border-radius:12px;font-weight:bold;font-size:14px;">{sj.score:.1f}</span>
          </td>
          <td style="padding:10px;border-bottom:1px solid #eee;color:#555;font-size:13px;">
            {sj.application_angle or sj.reasoning}
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;color:#333;">
  <div style="background:#2C3E50;padding:20px;border-radius:8px 8px 0 0;">
    <h2 style="color:white;margin:0;">🎯 JobRadar Daily Digest</h2>
    <p style="color:#BDC3C7;margin:5px 0 0;">{today} · {len(all_qualifying)} new matches
      (≥{min_score}) · {total} total scanned</p>
  </div>
  <table style="width:100%;border-collapse:collapse;background:white;
    border:1px solid #ddd;border-top:none;">
    <thead>
      <tr style="background:#ECF0F1;">
        <th style="padding:10px;text-align:left;">Job</th>
        <th style="padding:10px;width:70px;">Score</th>
        <th style="padding:10px;text-align:left;">Why it fits</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="color:#999;font-size:12px;text-align:center;margin-top:15px;">
    Sent by JobRadar · Open your Excel tracker at outputs/jobs_pipeline.xlsx
  </p>
</body>
</html>"""


def _build_text(
    jobs: list[ScoredJob],
    all_qualifying: list[ScoredJob],
    total: int,
    min_score: float,
) -> str:
    today = date.today().isoformat()
    lines = [
        f"JobRadar Daily Digest — {today}",
        f"{len(all_qualifying)} new matches (score ≥{min_score}) from {total} jobs scanned",
        "=" * 60,
    ]
    for i, sj in enumerate(jobs, 1):
        remote = " [Remote]" if sj.job.remote else ""
        lines += [
            f"\n{i}. {sj.job.title} @ {sj.job.company} — {sj.score:.1f}/10",
            f"   {sj.job.location}{remote} · {sj.job.source} · {sj.job.date_posted}",
            f"   {sj.application_angle or sj.reasoning}",
            f"   {sj.job.url}",
        ]
    return "\n".join(lines)
