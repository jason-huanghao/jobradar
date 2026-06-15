"""Freshness & expiry date math — single source of truth.

Used by hard_filter (pre-scoring drop of stale RawJobs) and by the sweep
(post-persist flip of stale Job rows). All datetimes are timezone-naive UTC.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from dateutil import parser as dateutil_parser


def parse_date(s: str) -> datetime | None:
    """Tolerant parse. Empty or unparseable input returns None (never raises)."""
    if not s:
        return None
    try:
        return dateutil_parser.parse(s, ignoretz=True)
    except Exception:
        return None


def compute_expires_at(date_posted: str, valid_through: str, ttl_days: int) -> str:
    """Objective deadline as an ISO string = earliest of:
      - valid_through (if parseable)
      - date_posted + ttl_days (if date_posted parseable)
    Returns "" when neither signal is known.
    """
    candidates: list[datetime] = []
    vt = parse_date(valid_through)
    if vt is not None:
        candidates.append(vt)
    dp = parse_date(date_posted)
    if dp is not None:
        candidates.append(dp + timedelta(days=ttl_days))
    if not candidates:
        return ""
    return min(candidates).isoformat()


def is_expired(expires_at: str, last_seen_at: datetime, now: datetime,
               staleness_days: int) -> bool:
    """True if the stored deadline has passed OR the job hasn't been re-seen
    within the staleness window."""
    ea = parse_date(expires_at)
    if ea is not None and ea <= now:
        return True
    if last_seen_at + timedelta(days=staleness_days) <= now:
        return True
    return False


def is_too_old(date_posted: str, valid_through: str, now: datetime,
               ttl_days: int) -> bool:
    """Pre-scoring drop check. True if the posting is older than the TTL or its
    explicit deadline has already passed."""
    vt = parse_date(valid_through)
    if vt is not None and vt < now:
        return True
    dp = parse_date(date_posted)
    if dp is not None and dp < now - timedelta(days=ttl_days):
        return True
    return False
