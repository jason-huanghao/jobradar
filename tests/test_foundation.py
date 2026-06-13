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
