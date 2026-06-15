"""Source reliability tests (sub-project #3). No network, no LLM."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from jobradar.config import AppConfig
from jobradar.models.job import RawJob, SearchQuery
from jobradar.sources.base import JobSource, SourceError
from jobradar.sources.health import (
    SourceOutcome,
    classify,
    status_is_failure,
)


def _mem_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


NOW = datetime(2026, 6, 16, 12, 0, 0)


# ── health.classify ───────────────────────────────────────────────
def test_classify_ok_and_empty():
    assert classify(5, None) == "ok"
    assert classify(0, None) == "empty"


def test_classify_error_and_blocked():
    assert classify(0, ValueError("boom")) == "error"
    assert classify(0, SourceError("nope", blocked=True)) == "blocked"
    assert classify(0, SourceError("nope")) == "error"


def test_classify_error_beats_jobs():
    # An error wins even if some jobs slipped through.
    assert classify(3, SourceError("partial")) == "error"


def test_status_is_failure():
    assert status_is_failure("error") is True
    assert status_is_failure("blocked") is True
    assert status_is_failure("empty") is False
    assert status_is_failure("ok") is False


# ── SourceOutcome round-trip / truncation ─────────────────────────
def test_outcome_round_trip():
    o = SourceOutcome("stepstone", "ok", 12, 345, attempts=2, error="")
    assert SourceOutcome.from_dict(o.to_dict()) == o


def test_outcome_truncates_error():
    o = SourceOutcome("x", "error", 0, 0, error="E" * 500)
    assert len(o.error) == 200


# ── SourceError + base.kind ───────────────────────────────────────
def test_source_error_blocked_flag():
    assert SourceError("x", blocked=True).blocked is True
    assert SourceError("x").blocked is False


def test_base_kind_default():
    assert JobSource.kind == "scraper"


def test_adapter_kinds():
    from jobradar.sources.adapters.arbeitsagentur import ArbeitsagenturSource
    from jobradar.sources.adapters.jobspy_adapter import JobSpySource
    from jobradar.sources.adapters.stepstone import StepstoneSource

    assert ArbeitsagenturSource.kind == "api"
    assert JobSpySource.kind == "library"
    assert StepstoneSource.kind == "scraper"


# ── ReliabilityConfig ─────────────────────────────────────────────
def test_reliability_config_defaults():
    cfg = AppConfig()
    assert cfg.reliability.max_attempts == 2
    assert cfg.reliability.retry_base_delay == 0.5


def test_reliability_config_override(tmp_path):
    from jobradar.config import load_config
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("reliability:\n  max_attempts: 4\n  retry_base_delay: 0.0\n")
    cfg = load_config(cfg_file)
    assert cfg.reliability.max_attempts == 4
    assert cfg.reliability.retry_base_delay == 0.0


# ── Registry instrumentation + retry ──────────────────────────────
class _FakeSource(JobSource):
    source_id = "fake"

    def __init__(self, behaviors):
        # behaviors: list of either a list[RawJob] to return or an Exception to raise.
        self._behaviors = behaviors
        self.calls = 0

    def is_enabled(self, config) -> bool:
        return True

    def fetch(self, queries, since):
        b = self._behaviors[min(self.calls, len(self._behaviors) - 1)]
        self.calls += 1
        if isinstance(b, Exception):
            raise b
        return b


def _registry_with(source):
    from jobradar.sources.registry import SourceRegistry
    reg = SourceRegistry()
    reg.register(source)
    return reg


def _cfg_no_sleep(max_attempts):
    cfg = AppConfig()
    cfg.reliability.max_attempts = max_attempts
    cfg.reliability.retry_base_delay = 0.0
    return cfg


_Q = [SearchQuery(keyword="dev", source="fake")]
_JOB = [RawJob(id="j1", title="Eng", url="https://x/1", source="fake")]


def test_registry_retries_then_succeeds():
    src = _FakeSource([SourceError("blip"), SourceError("blip"), _JOB])
    reg = _registry_with(src)
    jobs = reg.fetch_all(_Q, _cfg_no_sleep(3), NOW)
    assert len(jobs) == 1
    assert len(reg.last_outcomes) == 1
    o = reg.last_outcomes[0]
    assert o.status == "ok" and o.attempts == 3


def test_registry_exhausts_retries_blocked():
    src = _FakeSource([SourceError("blocked!", blocked=True)])
    reg = _registry_with(src)
    jobs = reg.fetch_all(_Q, _cfg_no_sleep(2), NOW)
    assert jobs == []
    o = reg.last_outcomes[0]
    assert o.status == "blocked" and o.attempts == 2


def test_registry_no_retry_on_plain_exception():
    src = _FakeSource([ValueError("bug")])
    reg = _registry_with(src)
    reg.fetch_all(_Q, _cfg_no_sleep(3), NOW)
    o = reg.last_outcomes[0]
    assert o.status == "error" and o.attempts == 1   # not retried


def test_registry_empty_and_ok():
    reg_empty = _registry_with(_FakeSource([[]]))
    reg_empty.fetch_all(_Q, _cfg_no_sleep(2), NOW)
    assert reg_empty.last_outcomes[0].status == "empty"

    reg_ok = _registry_with(_FakeSource([_JOB]))
    reg_ok.fetch_all(_Q, _cfg_no_sleep(2), NOW)
    assert reg_ok.last_outcomes[0].status == "ok"


# ── StepStone / XING raise SourceError ────────────────────────────
class _Resp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


@pytest.mark.parametrize("status,blocked", [(403, True), (429, True), (500, False)])
def test_stepstone_raises_on_non_200(monkeypatch, status, blocked):
    import httpx

    from jobradar.sources.adapters.stepstone import StepstoneSource
    monkeypatch.setattr(httpx.Client, "get", lambda self, *a, **k: _Resp(status))
    with pytest.raises(SourceError) as ei:
        StepstoneSource().fetch([SearchQuery(keyword="dev", source="stepstone")], NOW)
    assert ei.value.blocked is blocked


def test_xing_raises_on_403(monkeypatch):
    import httpx

    from jobradar.sources.adapters.xing import XingSource
    monkeypatch.setattr(httpx.Client, "get", lambda self, *a, **k: _Resp(403))
    with pytest.raises(SourceError) as ei:
        XingSource().fetch([SearchQuery(keyword="dev", source="xing")], NOW)
    assert ei.value.blocked is True


# ── recent_source_health aggregation ──────────────────────────────
def _run_row(started, outcomes):
    import json

    from jobradar.storage.models import PipelineRun
    return PipelineRun(
        mode="full", started_at=started,
        sources_run=json.dumps([o.to_dict() for o in outcomes]),
    )


def test_recent_source_health_aggregates():
    from jobradar.storage.repo import recent_source_health
    eng = _mem_engine()
    with Session(eng) as s:
        # oldest → newest
        s.add(_run_row(NOW - timedelta(days=3), [
            SourceOutcome("stepstone", "ok", 10, 5),
            SourceOutcome("xing", "ok", 4, 5),
        ]))
        s.add(_run_row(NOW - timedelta(days=2), [
            SourceOutcome("stepstone", "blocked", 0, 5),
        ]))
        s.add(_run_row(NOW - timedelta(days=1), [
            SourceOutcome("stepstone", "error", 0, 5),
            SourceOutcome("xing", "empty", 0, 5),
        ]))
        s.commit()
        health = recent_source_health(s)

    st = health["stepstone"]
    assert st["last_status"] == "error"
    assert st["consecutive_failures"] == 2          # error (newest) + blocked
    assert st["last_ok_at"] is not None              # the day-3 ok run

    xi = health["xing"]
    assert xi["last_status"] == "empty"
    assert xi["consecutive_failures"] == 0           # empty is not a failure


def test_recent_source_health_empty_db():
    from jobradar.storage.repo import recent_source_health
    eng = _mem_engine()
    with Session(eng) as s:
        assert recent_source_health(s) == {}


# ── pipeline persists sources_run ─────────────────────────────────
def test_pipeline_persists_sources_run(tmp_path, monkeypatch):
    import json

    from sqlmodel import select

    import jobradar.pipeline as pl
    from jobradar.models.candidate import CandidateProfile
    from jobradar.models.job import ScoreBreakdown, ScoredJob
    from jobradar.storage.db import get_session, init_db
    from jobradar.storage.models import PipelineRun

    db = tmp_path / "jobradar.db"
    init_db(db)
    cfg = AppConfig()
    cfg.user.email = "a@x.com"
    cfg.server.db_path = str(db)
    cfg._config_dir = tmp_path

    monkeypatch.setattr(pl, "LLMClient", lambda *a, **k: object())
    prof = CandidateProfile()
    prof.personal.name = "A"
    monkeypatch.setattr(pl, "ingest", lambda *a, **k: prof)
    monkeypatch.setattr(pl, "build_queries", lambda *a, **k: [])
    rj = RawJob(id="j1", title="Eng", company="Co", url="https://x/1", source="fake")

    def fake_fetch_all(self, *a, **k):
        self.last_outcomes = [SourceOutcome("fake", "ok", 1, 7, attempts=1)]
        return [rj]

    monkeypatch.setattr(pl.SourceRegistry, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(pl, "hard_filter", lambda jobs, cfg: (jobs, 0))
    sj = ScoredJob(job=rj, score=8.0, breakdown=ScoreBreakdown(skills_match=8.0))
    monkeypatch.setattr(pl, "score_jobs", lambda *a, **k: [sj])
    monkeypatch.setattr(pl, "optimize_cv", lambda *a, **k: ("cv", []))
    monkeypatch.setattr(pl, "generate_cover_letter", lambda *a, **k: "cl")

    pipe = pl.JobRadarPipeline(cfg, user_email="a@x.com")
    result = pipe.run(mode="full")

    with next(get_session(db)) as s:
        run = s.exec(select(PipelineRun).where(PipelineRun.id == result.run_id)).one()
        parsed = json.loads(run.sources_run)
    assert parsed == [SourceOutcome("fake", "ok", 1, 7).to_dict()]


# ── CLI: jobradar sources ─────────────────────────────────────────
def test_cli_sources(tmp_path):
    from typer.testing import CliRunner

    from jobradar.interfaces.cli import app

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("server:\n  db_path: ./jobradar.db\n")
    result = CliRunner().invoke(app, ["sources", "--config", str(cfg_file)])
    assert result.exit_code == 0, result.output
    assert "stepstone" in result.output
    assert "arbeitsagentur" in result.output


# ── API: GET /api/sources ─────────────────────────────────────────
def test_api_sources(tmp_path):
    from fastapi.testclient import TestClient

    from jobradar.api.main import create_app
    from jobradar.storage.db import init_db

    db = tmp_path / "jobradar.db"
    init_db(db)
    cfg = AppConfig()
    cfg.server.db_path = str(db)
    cfg._config_dir = tmp_path

    client = TestClient(create_app(cfg))
    resp = client.get("/api/sources")
    assert resp.status_code == 200
    data = resp.json()
    ids = {r["source_id"] for r in data["sources"]}
    assert {"stepstone", "xing", "arbeitsagentur", "jobspy"} <= ids
    row = next(r for r in data["sources"] if r["source_id"] == "arbeitsagentur")
    assert row["kind"] == "api"
    assert "consecutive_failures" in row
