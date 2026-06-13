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
