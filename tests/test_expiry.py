"""Expiry & freshness tests. No LLM involved."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine


def _mem_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


NOW = datetime(2026, 6, 14, 12, 0, 0)


# ── freshness.compute_expires_at ──────────────────────────────────
def test_compute_expires_at_prefers_earliest():
    from jobradar.scoring.freshness import compute_expires_at
    # valid_through (2026-06-20) is earlier than date_posted+14 (2026-06-24)
    out = compute_expires_at("2026-06-10", "2026-06-20", ttl_days=14)
    assert out.startswith("2026-06-20")


def test_compute_expires_at_posting_only():
    from jobradar.scoring.freshness import compute_expires_at
    out = compute_expires_at("2026-06-10", "", ttl_days=14)
    assert out.startswith("2026-06-24")


def test_compute_expires_at_unknown():
    from jobradar.scoring.freshness import compute_expires_at
    assert compute_expires_at("", "", ttl_days=14) == ""
    assert compute_expires_at("garbage", "also bad", ttl_days=14) == ""


# ── freshness.is_expired ──────────────────────────────────────────
def test_is_expired_by_deadline():
    from jobradar.scoring.freshness import is_expired
    assert is_expired("2026-06-01", NOW, NOW, staleness_days=7) is True


def test_is_expired_by_staleness():
    from jobradar.scoring.freshness import is_expired
    old_seen = NOW - timedelta(days=10)
    assert is_expired("", old_seen, NOW, staleness_days=7) is True


def test_is_expired_stays_active():
    from jobradar.scoring.freshness import is_expired
    fresh_seen = NOW - timedelta(days=1)
    assert is_expired("", fresh_seen, NOW, staleness_days=7) is False
    assert is_expired("2026-12-31", fresh_seen, NOW, staleness_days=7) is False


# ── freshness.is_too_old ──────────────────────────────────────────
def test_is_too_old_by_posting_age():
    from jobradar.scoring.freshness import is_too_old
    # posted 20 days before NOW, ttl 14 -> too old
    assert is_too_old("2026-05-25", "", NOW, ttl_days=14) is True
    # posted 5 days before NOW -> fresh
    assert is_too_old("2026-06-09", "", NOW, ttl_days=14) is False


def test_is_too_old_by_past_deadline():
    from jobradar.scoring.freshness import is_too_old
    # recent posting but the deadline already passed -> too old
    assert is_too_old("2026-06-13", "2026-06-01", NOW, ttl_days=14) is True


def test_is_too_old_unparseable_keeps():
    from jobradar.scoring.freshness import is_too_old
    assert is_too_old("", "", NOW, ttl_days=14) is False
    assert is_too_old("not a date", "", NOW, ttl_days=14) is False


# ── RawJob carries valid_through ──────────────────────────────────
def test_rawjob_has_valid_through():
    from jobradar.models.job import RawJob
    j = RawJob(title="Eng", valid_through="2026-07-01")
    assert j.valid_through == "2026-07-01"
    assert RawJob(title="Eng").valid_through == ""


# ── hard_filter honors valid_through ──────────────────────────────
def test_hard_filter_drops_past_deadline():
    from jobradar.config import AppConfig
    from jobradar.models.job import RawJob
    from jobradar.scoring.hard_filter import apply as hard_filter

    cfg = AppConfig()
    recent = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    past = (datetime.utcnow() - timedelta(days=2)).date().isoformat()
    # recent posting, but deadline already passed -> dropped
    jobs = [RawJob(title="Eng", date_posted=recent, valid_through=past)]
    kept, dropped = hard_filter(jobs, cfg)
    assert kept == [] and dropped == 1


# ── sweep_expired ─────────────────────────────────────────────────
def test_sweep_flips_stale_and_is_idempotent():
    from jobradar.storage.models import Job
    from jobradar.storage.repo import sweep_expired

    eng = _mem_engine()
    with Session(eng) as s:
        old_seen = NOW - timedelta(days=30)
        fresh_seen = NOW - timedelta(days=1)
        # by past deadline
        s.add(Job(id="dead", source="t", title="A", url="https://x/1",
                  expires_at="2026-06-01", last_seen_at=fresh_seen))
        # by staleness (no deadline, not seen in 30 days)
        s.add(Job(id="stale", source="t", title="B", url="https://x/2",
                  expires_at="", last_seen_at=old_seen))
        # fresh: no deadline, recently seen
        s.add(Job(id="live", source="t", title="C", url="https://x/3",
                  expires_at="", last_seen_at=fresh_seen))
        s.commit()

        count = sweep_expired(s, NOW, staleness_days=7)
        assert count == 2
        assert s.get(Job, "dead").status == "expired"
        assert s.get(Job, "stale").status == "expired"
        assert s.get(Job, "live").status == "active"

        # second run is a no-op
        assert sweep_expired(s, NOW, staleness_days=7) == 0


# ── list_scored hides expired by default ──────────────────────────
def test_list_scored_hides_expired_by_default():
    from jobradar.storage import repo
    from jobradar.storage.models import Job, Score

    eng = _mem_engine()
    with Session(eng) as s:
        repo.resolve_or_create_user(s, "a@x.com")
        p = repo.create_profile_version(s, "a@x.com", "cv.md", "{}")
        s.add(Job(id="live", source="t", title="A", url="https://x/1", status="active"))
        s.add(Job(id="gone", source="t", title="B", url="https://x/2", status="expired"))
        s.add(Score(profile_id=p.id, job_id="live", overall=8.0))
        s.add(Score(profile_id=p.id, job_id="gone", overall=9.0))
        s.commit()

        default_ids = [job.id for _, job in repo.list_scored(s, p.id)]
        assert default_ids == ["live"]

        all_ids = sorted(job.id for _, job in repo.list_scored(s, p.id, include_expired=True))
        assert all_ids == ["gone", "live"]


# ── pipeline persist: insert-or-touch ─────────────────────────────
def test_persist_sets_expires_at_and_touches_seen():
    from jobradar.models.job import RawJob
    from jobradar.pipeline import _persist_jobs
    from jobradar.storage.models import Job

    eng = _mem_engine()
    posted = (NOW - timedelta(days=2)).date().isoformat()
    with Session(eng) as s:
        # first sighting: inserts with computed expires_at
        new1 = _persist_jobs(
            s, [RawJob(id="j1", source="t", title="Eng", url="https://x/1",
                       date_posted=posted, valid_through="")],
            ttl_days=14, now=NOW,
        )
        assert new1 == 1
        row = s.get(Job, "j1")
        assert row.expires_at != ""
        assert row.expires_at.startswith("2026")   # posted + 14 days
        first_seen = row.last_seen_at

        # re-sighting later with a now-known deadline: touches last_seen + backfills
        later = NOW + timedelta(days=1)
        new2 = _persist_jobs(
            s, [RawJob(id="j1", source="t", title="Eng", url="https://x/1",
                       date_posted=posted, valid_through="2026-06-20")],
            ttl_days=14, now=later,
        )
        assert new2 == 0
        row = s.get(Job, "j1")
        assert row.last_seen_at == later and row.last_seen_at != first_seen
        assert row.valid_through == "2026-06-20"
        assert row.expires_at.startswith("2026-06-20")
