"""Foundation tests — schema, scoping, versioning, identity. LLM is mocked."""
from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine


def _mem_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


def test_schema_round_trip():
    from jobradar.storage.models import User, Profile, Job, Score
    eng = _mem_engine()
    with Session(eng) as s:
        s.add(User(email="a@x.com", display_name="A"))
        s.add(Profile(id="p1", user_email="a@x.com", version=1,
                      cv_source="cv.md", profile_json="{}", is_active=True))
        s.add(Job(id="j1", source="test", title="Eng", url="https://x/1"))
        s.add(Score(profile_id="p1", job_id="j1", overall=8.0))
        s.commit()
        score = s.get(Score, ("p1", "j1"))
        assert score is not None and score.overall == 8.0


def test_init_db_creates_tables(tmp_path):
    from jobradar.storage.db import init_db, get_session
    from jobradar.storage.models import User
    from sqlmodel import select
    db = tmp_path / "jobradar.db"
    init_db(db)
    with next(get_session(db)) as s:
        s.add(User(email="b@x.com"))
        s.commit()
        assert s.exec(select(User)).first().email == "b@x.com"


def test_profile_versioning():
    from jobradar.storage import repo
    from jobradar.storage.models import Profile
    from sqlmodel import select
    eng = _mem_engine()
    with Session(eng) as s:
        repo.resolve_or_create_user(s, "a@x.com")
        p1 = repo.create_profile_version(s, "a@x.com", "cv_v1.md", '{"v":1}')
        p2 = repo.create_profile_version(s, "a@x.com", "cv_v2.md", '{"v":2}')
        s.commit()
        assert p1.version == 1 and p2.version == 2
        active = repo.get_active_profile(s, "a@x.com")
        assert active.id == p2.id
        rows = s.exec(select(Profile).where(Profile.is_active == True)).all()  # noqa: E712
        assert len(rows) == 1


def test_score_scoping():
    from jobradar.storage import repo
    from jobradar.storage.models import Job, Score
    eng = _mem_engine()
    with Session(eng) as s:
        for email in ("a@x.com", "b@x.com"):
            repo.resolve_or_create_user(s, email)
            repo.create_profile_version(s, email, "cv.md", "{}")
        s.add(Job(id="j1", source="t", title="Eng", url="https://x/1"))
        pa = repo.get_active_profile(s, "a@x.com")
        pb = repo.get_active_profile(s, "b@x.com")
        s.add(Score(profile_id=pa.id, job_id="j1", overall=9.0))
        s.add(Score(profile_id=pb.id, job_id="j1", overall=3.0))
        s.commit()
        a_scores = repo.scored_job_ids(s, pa.id)
        assert a_scores == {"j1"}
        rows = repo.list_scored(s, pa.id)
        assert len(rows) == 1 and rows[0][0].overall == 9.0


def test_resolve_user_email():
    import pytest
    from jobradar.config import AppConfig, resolve_user_email
    cfg = AppConfig()
    cfg.user.email = "config@x.com"
    assert resolve_user_email(cfg, None) == "config@x.com"
    assert resolve_user_email(cfg, "flag@x.com") == "flag@x.com"   # flag wins
    cfg.user.email = ""
    with pytest.raises(ValueError, match="user email"):
        resolve_user_email(cfg, None)


def test_pipeline_scopes_scores(tmp_path, monkeypatch):
    """Pipeline writes Score rows keyed on the active profile; skips re-scoring."""
    from jobradar.config import AppConfig
    from jobradar.storage.db import init_db, get_session
    from jobradar.storage import repo
    from jobradar.models.job import RawJob, ScoredJob, ScoreBreakdown
    from jobradar.models.candidate import CandidateProfile
    import jobradar.pipeline as pl

    db = tmp_path / "jobradar.db"
    init_db(db)
    cfg = AppConfig()
    cfg.user.email = "a@x.com"
    cfg.server.db_path = str(db)
    cfg._config_dir = tmp_path

    # Stub the expensive bits: LLM client, CV ingest, source fetch, scorer, generators.
    monkeypatch.setattr(pl, "LLMClient", lambda *a, **k: object())
    prof = CandidateProfile(); prof.personal.name = "A"
    monkeypatch.setattr(pl, "ingest", lambda *a, **k: prof)
    monkeypatch.setattr(pl, "build_queries", lambda *a, **k: [])
    rj = RawJob(id="j1", title="Eng", company="Co", url="https://x/1", source="test")
    monkeypatch.setattr(pl.SourceRegistry, "fetch_all", lambda self, *a, **k: [rj])
    monkeypatch.setattr(pl, "hard_filter", lambda jobs, cfg: (jobs, 0))
    sj = ScoredJob(job=rj, score=8.0, breakdown=ScoreBreakdown(skills_match=8.0))
    monkeypatch.setattr(pl, "score_jobs", lambda *a, **k: [sj])
    monkeypatch.setattr(pl, "optimize_cv", lambda *a, **k: ("cv", []))
    monkeypatch.setattr(pl, "generate_cover_letter", lambda *a, **k: "cl")

    pipe = pl.JobRadarPipeline(cfg, user_email="a@x.com")
    result = pipe.run(mode="full")
    assert result.jobs_scored == 1

    with next(get_session(db)) as s:
        p = repo.get_active_profile(s, "a@x.com")
        assert repo.scored_job_ids(s, p.id) == {"j1"}


def test_list_jobs_isolated(tmp_path):
    from fastapi.testclient import TestClient
    from jobradar.config import AppConfig
    from jobradar.api.main import create_app
    from jobradar.storage.db import init_db, get_session
    from jobradar.storage import repo
    from jobradar.storage.models import Job, Score

    db = tmp_path / "jobradar.db"
    init_db(db)
    cfg = AppConfig()
    cfg.user.email = "a@x.com"
    cfg.server.db_path = str(db)
    cfg._config_dir = tmp_path

    with next(get_session(db)) as s:
        for email in ("a@x.com", "b@x.com"):
            repo.resolve_or_create_user(s, email)
            repo.create_profile_version(s, email, "cv.md", "{}")
        s.add(Job(id="j1", source="t", title="Eng", url="https://x/1"))
        pa = repo.get_active_profile(s, "a@x.com")
        pb = repo.get_active_profile(s, "b@x.com")
        s.add(Score(profile_id=pa.id, job_id="j1", overall=9.0))
        s.add(Score(profile_id=pb.id, job_id="j1", overall=3.0))
        s.commit()

    client = TestClient(create_app(cfg))
    r = client.get("/api/jobs", params={"user_email": "a@x.com"})
    body = r.json()
    assert body["total"] == 1
    assert body["jobs"][0]["score"] == 9.0   # A's score, not B's


def test_apply_engine_scoped(tmp_path):
    from jobradar.apply.engine import run_apply
    from jobradar.storage.db import init_db, get_session
    from jobradar.storage import repo
    from jobradar.storage.models import Job, Score

    db = tmp_path / "jobradar.db"
    init_db(db)
    with next(get_session(db)) as s:
        for email in ("a@x.com", "b@x.com"):
            repo.resolve_or_create_user(s, email)
            repo.create_profile_version(s, email, "cv.md", "{}")
        s.add(Job(id="j1", source="bosszhipin", title="AI", url="https://www.zhipin.com/job/1"))
        pa = repo.get_active_profile(s, "a@x.com")
        pb = repo.get_active_profile(s, "b@x.com")
        s.add(Score(profile_id=pa.id, job_id="j1", overall=9.0))   # A: eligible
        s.add(Score(profile_id=pb.id, job_id="j1", overall=2.0))   # B: not
        s.commit()
        a_id, b_id = pa.id, pb.id

    sess = run_apply(db_path=db, profile_id=a_id, min_score=7.5,
                     dry_run=True, platforms=["bosszhipin"])
    assert len(sess.results) == 1
    # B's low score must not leak in via A's run
    sess_b = run_apply(db_path=db, profile_id=b_id, min_score=7.5,
                       dry_run=True, platforms=["bosszhipin"])
    assert len(sess_b.results) == 0
