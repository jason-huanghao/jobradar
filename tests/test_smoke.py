"""Sprint 0 smoke tests — import correctness, config defaults, core utilities."""

from __future__ import annotations

import json
import os
from pathlib import Path


# ── 1. Module imports ─────────────────────────────────────────────

def test_imports():
    import jobradar.config
    import jobradar.llm.env_probe
    import jobradar.llm.client
    import jobradar.models.candidate
    import jobradar.models.job
    import jobradar.profile.ingestor
    import jobradar.sources.normalizer
    import jobradar.scoring.hard_filter
    import jobradar.interfaces.skill
    import jobradar.interfaces.cli


# ── 2. Config defaults ────────────────────────────────────────────

def test_config_defaults():
    from jobradar.config import AppConfig
    cfg = AppConfig()
    # CV starts empty — user must provide
    assert cfg.candidate.effective_cv() == ""
    # All EU sources on by default
    assert cfg.sources.arbeitsagentur.enabled is True
    assert cfg.sources.jobspy.enabled is True
    assert cfg.sources.stepstone.enabled is True
    assert cfg.sources.xing.enabled is True
    # CN sources off by default
    assert cfg.sources.bosszhipin.enabled is False
    assert cfg.sources.lagou.enabled is False
    assert cfg.sources.zhilian.enabled is False
    # Thresholds
    assert cfg.scoring.auto_apply_min_score == 7.5
    assert cfg.scoring.min_score_digest == 6.0
    assert cfg.scoring.min_score_application == 7.0
    # Locations: empty = worldwide
    assert cfg.search.locations == []


# ── 3. Config cv field resolution ────────────────────────────────

def test_config_cv_override():
    from jobradar.config import load_config
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = load_config(Path(tmpdir) / "config.yaml", cv_override="https://example.com/cv.md")
        assert cfg.candidate.effective_cv() == "https://example.com/cv.md"


# ── 4. Normalizer + dedup ─────────────────────────────────────────

def test_normalizer_dedup():
    from jobradar.sources.normalizer import normalise, dedup
    from jobradar.models.job import RawJob

    def make_job(url: str) -> RawJob:
        return RawJob(
            id="", title="Engineer", company="ACME", location="Berlin",
            url=url, description="desc", source="test",
            date_posted="2026-03-17",
        )

    j1 = normalise(make_job("https://example.com/job/1"))
    j2 = normalise(make_job("https://example.com/job/1"))  # duplicate
    j3 = normalise(make_job("https://example.com/job/2"))

    assert j1.id == j2.id  # same URL → same hash
    assert j1.id != j3.id

    deduped = dedup([j1, j2, j3])
    assert len(deduped) == 2


# ── 5. Hard filter ────────────────────────────────────────────────

def test_hard_filter_drops_excluded():
    from jobradar.scoring.hard_filter import apply as hard_filter
    from jobradar.models.job import RawJob
    from jobradar.config import AppConfig

    cfg = AppConfig()

    def job(title: str) -> RawJob:
        return RawJob(
            id=title, title=title, company="Co", location="Berlin",
            url=f"https://x.com/{title}", description="desc", source="test",
            date_posted="2026-03-17",
        )

    jobs = [job("Senior Engineer"), job("Praktikum Backend"), job("Werkstudent AI")]
    kept, dropped = hard_filter(jobs, cfg)
    assert len(kept) == 1
    assert kept[0].title == "Senior Engineer"
    assert dropped == 2


# ── 6. env_probe: no keys available returns None ─────────────────

def test_env_probe_no_keys(monkeypatch):
    """With all keys unset and no local servers, detect_endpoint returns None."""
    from jobradar.llm import env_probe

    all_vars = [row[1] for row in env_probe._PROBE_TABLE]
    for var in all_vars:
        monkeypatch.delenv(var, raising=False)

    # Stub out OAuth and port checks
    monkeypatch.setattr(env_probe, "_load_claude_oauth", lambda: None)
    monkeypatch.setattr(env_probe, "_port_open", lambda *a, **kw: False)

    result = env_probe.detect_endpoint()
    assert result is None


# ── 7. Skill setup: check_only returns structured JSON ────────────

def test_skill_setup_check_only(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBRADAR_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    from jobradar.interfaces.skill import run_skill
    result = json.loads(run_skill("setup", json.dumps({"check_only": True})))
    assert "status" in result
    assert "missing" in result
    assert "prompt_for_user" in result


# ── 8. Skill setup: cv_content writes file ────────────────────────

def test_skill_setup_cv_content(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBRADAR_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    from jobradar.interfaces.skill import run_skill
    cv_text = "# Jane Doe\nSoftware Engineer with Python and ML."
    result = json.loads(run_skill("setup", json.dumps({"cv_content": cv_text})))

    cv_file = tmp_path / "cv" / "cv_current.md"
    assert cv_file.exists()
    assert "Jane Doe" in cv_file.read_text()


# ── 10. Report generation — produces valid HTML ───────────────────

def test_report_generates_html(tmp_path):
    from jobradar.report.generator import generate_report

    jobs = [
        {
            "id": "job1", "title": "AI Engineer", "company": "ACME GmbH",
            "location": "Berlin", "score": 8.5, "source": "stepstone",
            "url": "https://example.com/job/1", "date_posted": "2026-03-15",
            "reasoning": "Great skills match.",
            "breakdown": {
                "skills_match": 9.0, "seniority_fit": 8.0, "location_fit": 9.0,
                "language_fit": 8.0, "visa_friendly": 7.0, "growth_potential": 8.5,
            },
        },
        {
            "id": "job2", "title": "ML Engineer", "company": "TechCorp",
            "location": "Remote", "score": 7.2, "source": "jobspy:indeed",
            "url": "https://example.com/job/2", "date_posted": "2026-03-14",
            "reasoning": "Good potential.",
            "breakdown": {
                "skills_match": 7.0, "seniority_fit": 7.5, "location_fit": 10.0,
                "language_fit": 7.0, "visa_friendly": 8.0, "growth_potential": 7.0,
            },
        },
    ]
    out = tmp_path / "test_report.html"
    path = generate_report(jobs, profile_name="Hao Huang", output_path=out)

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "AI Engineer" in content
    assert "ACME GmbH" in content
    assert "8.5" in content
    assert "JobRadar" in content
    assert "JOBS = " in content   # embedded JSON data


# ── 11. Report filters by min_score ──────────────────────────────

def test_report_score_filter(tmp_path):
    from jobradar.report.generator import generate_report

    jobs = [
        {"id": "a", "title": "Senior Dev", "company": "X", "location": "Berlin",
         "score": 9.0, "source": "stepstone", "url": "", "date_posted": "2026-03-15",
         "reasoning": "", "breakdown": {}},
        {"id": "b", "title": "Junior Dev", "company": "Y", "location": "Munich",
         "score": 5.0, "source": "jobspy:indeed", "url": "", "date_posted": "2026-03-15",
         "reasoning": "", "breakdown": {}},
    ]
    # The generator writes all jobs; filtering happens client-side via JS
    # So both should appear in the HTML (filtering is in JS, not Python)
    out = tmp_path / "report_filter.html"
    path = generate_report(jobs, output_path=out)
    content = path.read_text()
    assert "Senior Dev" in content
    assert "Junior Dev" in content
    assert '"score": 9.0' in content or "9.0" in content


def test_query_builder_max_results():
    from jobradar.sources.query_builder import build_queries
    from jobradar.config import AppConfig
    from jobradar.models.candidate import CandidateProfile

    cfg = AppConfig()
    cfg.search.max_results_per_source = 7

    profile = CandidateProfile()
    profile.personal.name = "Test User"
    profile.skills.technical = ["Python"]

    queries = build_queries(profile, cfg, max_results_override=3)
    for q in queries:
        assert q.extra.get("max_results", 3) <= 3


# ── 12. Apply history — dedup and daily count ─────────────────────

def test_apply_history(tmp_path):
    from jobradar.apply.history import ApplyHistory

    h = ApplyHistory(path=tmp_path / "apply_history.json")
    assert not h.already_applied("job1")
    assert h.daily_count() == 0

    h.record("job1")
    assert h.already_applied("job1")
    assert h.daily_count() == 1
    assert not h.already_applied("job2")

    h.record("job2")
    assert h.daily_count() == 2
    assert h.total_applied() == 2


# ── 13. Apply engine — dry-run returns DRY_RUN status ────────────

def test_apply_engine_dry_run(tmp_path):
    from jobradar.apply.engine import run_apply
    from jobradar.storage.db import init_db
    from jobradar.storage.models import Job, ScoredJobRecord
    from sqlmodel import Session, create_engine

    db_path = tmp_path / "test.db"
    init_db(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        session.add(Job(
            id="zboss1", title="AI工程师", company="字节跳动",
            location="北京", url="https://www.zhipin.com/job/zboss1",
            description="AI job", source="bosszhipin",
            date_posted="2026-03-15", job_type="fulltime",
            salary="", remote=False, raw_extra="{}",
        ))
        session.add(ScoredJobRecord(
            job_id="zboss1", candidate_id="test",
            overall=8.5, skills_match=9.0, seniority_fit=8.0,
            location_fit=8.0, language_fit=9.0, visa_friendly=7.0,
            growth_potential=8.5, reasoning="great match",
        ))
        session.commit()

    result = run_apply(
        db_path=db_path,
        min_score=7.5,
        dry_run=True,
        confirm_each=False,
        platforms=["bosszhipin"],
    )
    assert len(result.results) == 1
    assert result.results[0].status.value == "dry_run"


# ── 14. Boss helper functions ─────────────────────────────────────

def test_boss_helpers():
    from jobradar.apply.boss import _is_inactive_hr, _format_greeting

    assert _is_inactive_hr("3个月前活跃", 7) is True
    assert _is_inactive_hr("3天前活跃", 7) is False
    assert _is_inactive_hr("10天前活跃", 7) is True
    assert _is_inactive_hr("半年前活跃", 7) is True

    greeting = _format_greeting(
        "Hello $company, I want $title",
        {"title": "工程师", "company": "ACME"}
    )
    assert greeting == "Hello ACME, I want 工程师"
