# JobRadar Foundation (User Model + Clean Schema) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild JobRadar's data foundation as a clean six-table multi-tenant schema (user → versioned profile → score) with Alembic migrations and per-user scoping threaded through the pipeline and all read paths.

**Architecture:** Fresh schema (old `jobradar.db` is discarded — no import). Identity is `user.email`, resolved explicitly from flag/arg/config. A `profile` is a versioned CV under a user; `score`/`application` key on `profile_id`; the `job` table stays global and shared. Alembic is the schema source of truth; `init_db` upgrades to head. All read paths (`jobs.py`, `apply/engine.py`, `report/`) filter by the active profile, fixing the blended/arbitrary-candidate bug.

**Tech Stack:** Python 3.11, SQLModel + SQLAlchemy, Alembic, Pydantic v2, FastAPI, pytest (LLM mocked).

**Spec:** `docs/superpowers/specs/2026-06-13-foundation-user-model-design.md`

**Branch:** `refactor/foundation-user-model` (already created).

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `src/jobradar/storage/models.py` | The six SQLModel tables | Rewrite |
| `src/jobradar/storage/db.py` | Engine + `init_db` via Alembic upgrade | Rewrite |
| `src/jobradar/storage/repo.py` | User/profile/score query helpers | Create |
| `alembic.ini`, `migrations/env.py`, `migrations/versions/*` | Alembic scaffolding + initial migration | Create |
| `src/jobradar/config.py` | `UserConfig`, `resolve_user_email` | Modify |
| `src/jobradar/pipeline.py` | `JobRadarPipeline(config, user_email)`, profile-scoped writes | Modify |
| `src/jobradar/api/deps.py` | FastAPI `get_db` / `get_user_email` dependencies | Create |
| `src/jobradar/api/routers/jobs.py` | Scoped `list_jobs` / `get_job` / status | Modify |
| `src/jobradar/apply/engine.py` | `_load_eligible_jobs(profile_id)`, callback confirm | Modify |
| `src/jobradar/report/generator.py` | (caller scopes; verify signature) | Verify/Modify |
| `src/jobradar/interfaces/cli.py` | `--user`, `init` prompt | Modify |
| `src/jobradar/interfaces/skill.py` | `user_email` arg | Modify |
| `src/jobradar/sources/adapters/stepstone.py` | Route IDs through `normalizer.make_id` | Modify |
| `tests/test_foundation.py` | New scoping/versioning/identity tests | Create |
| `tests/test_smoke.py` | Update obsolete-schema tests | Modify |
| `.github/workflows/ci.yml` | Run `pytest tests/` | Modify |
| `pyproject.toml` | Add `alembic` dependency | Modify |

---

## Task 1: New storage models (six tables)

**Files:**
- Modify: `src/jobradar/storage/models.py` (full rewrite)
- Test: `tests/test_foundation.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_foundation.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_foundation.py::test_schema_round_trip -v`
Expected: FAIL with `ImportError: cannot import name 'User'` (or `Score`).

- [ ] **Step 3: Write the new models**

Replace the entire contents of `src/jobradar/storage/models.py`:

```python
"""SQLModel table definitions — clean multi-tenant schema (v1).

user (email) → profile (versioned CV) → score/application (per profile).
job is global and shared across users.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """Stable identity. Holds settings/LLM config in later sub-projects."""

    email: str = Field(primary_key=True)
    display_name: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class Profile(SQLModel, table=True):
    """A versioned CV under a user. Exactly one is_active per user."""

    id: str = Field(primary_key=True)          # uuid4 hex
    user_email: str = Field(foreign_key="user.email", index=True)
    version: int = 1
    cv_source: str = ""                        # path or URL
    profile_json: str = Field(default="{}")    # serialized CandidateProfile
    is_active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)


class Job(SQLModel, table=True):
    """Global, objective job listing — shared across all users."""

    id: str = Field(primary_key=True)          # sha256(source + canonical_url)[:16]
    source: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    url: str = ""
    salary: str = ""
    remote: Optional[bool] = None
    job_type: str = "fulltime"
    raw_extra: str = Field(default="{}")
    date_posted: str = ""
    valid_through: str = ""                     # deadline (JSON-LD validThrough); "" if unknown
    expires_at: str = ""                        # computed; filtering logic is sub-project #2
    status: str = "active"                      # active | expired
    fetched_at: datetime = Field(default_factory=_utcnow)
    last_seen_at: datetime = Field(default_factory=_utcnow)


class Score(SQLModel, table=True):
    """LLM score for a (profile, job) pair."""

    profile_id: str = Field(primary_key=True, foreign_key="profile.id")
    job_id: str = Field(primary_key=True, foreign_key="job.id")
    overall: float = 0.0
    skills_match: float = 0.0
    seniority_fit: float = 0.0
    location_fit: float = 0.0
    language_fit: float = 0.0
    visa_friendly: float = 0.0
    growth_potential: float = 0.0
    reasoning: str = ""
    application_angle: str = ""
    status: str = "new"            # new | interested | applied | rejected | interview | offer
    applied: bool = False
    applied_at: Optional[datetime] = None
    scored_at: datetime = Field(default_factory=_utcnow)


class Application(SQLModel, table=True):
    """Generated CV + cover letter for a (profile, job) pair."""

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: str = Field(foreign_key="profile.id", index=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    cv_optimized_md: str = ""
    cover_letter_md: str = ""
    gaps: str = Field(default="[]")
    status: str = "draft"          # draft | sent | rejected | interview
    created_at: datetime = Field(default_factory=_utcnow)


class PipelineRun(SQLModel, table=True):
    """Record of each pipeline execution — now scoped to a user/profile."""

    __tablename__ = "pipeline_run"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_email: str = Field(default="", index=True)
    profile_id: str = ""
    mode: str = "full"             # full | quick | score-only | dry-run
    sources_run: str = Field(default="[]")
    jobs_fetched: int = 0
    jobs_new: int = 0
    jobs_scored: int = 0
    jobs_generated: int = 0
    status: str = "running"        # running | done | failed
    error: str = ""
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: Optional[datetime] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_foundation.py::test_schema_round_trip -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/storage/models.py tests/test_foundation.py
git commit -m "feat(storage): clean six-table multi-tenant schema"
```

---

## Task 2: Alembic scaffolding + init_db via upgrade

**Files:**
- Modify: `pyproject.toml` (add `alembic>=1.13`)
- Create: `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_initial.py`
- Modify: `src/jobradar/storage/db.py` (full rewrite)
- Test: `tests/test_foundation.py::test_init_db_creates_tables`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_foundation.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_foundation.py::test_init_db_creates_tables -v`
Expected: FAIL — `init_db` does not yet create tables via migrations (no migration exists).

- [ ] **Step 3: Add the alembic dependency**

In `pyproject.toml`, add to the `dependencies` list (under `# Storage`):

```toml
    "alembic>=1.13",
```

- [ ] **Step 4: Create `alembic.ini`** (repo root)

```ini
[alembic]
script_location = migrations
prepend_sys_path = src

[loggers]
keys = root

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[handler_console]
class = StreamHandler
args = (sys.stderr,)
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 5: Create `migrations/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 6: Create `migrations/env.py`**

```python
"""Alembic environment — uses SQLModel.metadata as the schema source of truth."""
from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# Import all models so metadata is populated.
import jobradar.storage.models  # noqa: F401

config = context.config
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Generate the initial migration**

Run (from repo root, with the venv active):

```bash
alembic -x db=sqlite:///./_tmp_autogen.db revision --autogenerate -m "initial" --rev-id 0001
```

If autogenerate cannot resolve the URL, temporarily add `sqlalchemy.url = sqlite:///./_tmp_autogen.db` under `[alembic]` in `alembic.ini`, run the command, then remove that line and delete `_tmp_autogen.db`.

Expected: a file `migrations/versions/0001_initial.py` containing `op.create_table("user", ...)`, `"profile"`, `"job"`, `"score"`, `"application"`, `"pipeline_run"`. Open it and confirm all six tables are present and `import sqlmodel` is at the top.

- [ ] **Step 8: Rewrite `src/jobradar/storage/db.py`**

```python
"""Database engine, session factory, and Alembic-backed initialisation."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

# Import all table models so SQLModel.metadata is populated.
from .models import (  # noqa: F401
    Application,
    Job,
    PipelineRun,
    Profile,
    Score,
    User,
)

_engines: dict[str, object] = {}
_REPO_ROOT = Path(__file__).resolve().parents[3]   # .../jobradar
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"


def get_engine(db_path: str | Path = "./jobradar.db"):
    key = str(Path(db_path).resolve())
    if key not in _engines:
        _engines[key] = create_engine(
            f"sqlite:///{key}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engines[key]


def init_db(db_path: str | Path = "./jobradar.db") -> None:
    """Create/upgrade the schema by running Alembic migrations to head."""
    path = Path(db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(cfg, "head")


def get_session(db_path: str | Path = "./jobradar.db") -> Generator[Session, None, None]:
    with Session(get_engine(Path(db_path).resolve())) as session:
        yield session
```

- [ ] **Step 9: Run test to verify it passes**

Run: `python -m pytest tests/test_foundation.py::test_init_db_creates_tables -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml alembic.ini migrations/ src/jobradar/storage/db.py tests/test_foundation.py
git commit -m "feat(storage): Alembic migrations; init_db upgrades to head"
```

---

## Task 3: User/profile/score repository helpers

**Files:**
- Create: `src/jobradar/storage/repo.py`
- Test: `tests/test_foundation.py::test_profile_versioning`, `::test_score_scoping`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_foundation.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_foundation.py::test_profile_versioning tests/test_foundation.py::test_score_scoping -v`
Expected: FAIL — `ModuleNotFoundError: jobradar.storage.repo`.

- [ ] **Step 3: Create `src/jobradar/storage/repo.py`**

```python
"""Query helpers for user / profile / score scoping. Pure functions over a Session."""

from __future__ import annotations

import uuid

from sqlmodel import Session, select

from .models import Job, Profile, Score, User


def resolve_or_create_user(session: Session, email: str, display_name: str = "") -> User:
    user = session.get(User, email)
    if user is None:
        user = User(email=email, display_name=display_name)
        session.add(user)
        session.flush()
    return user


def create_profile_version(
    session: Session, user_email: str, cv_source: str, profile_json: str
) -> Profile:
    """Create a new active profile version, deactivating any prior ones."""
    existing = session.exec(
        select(Profile).where(Profile.user_email == user_email)
    ).all()
    for p in existing:
        p.is_active = False
        session.add(p)
    next_version = max((p.version for p in existing), default=0) + 1
    profile = Profile(
        id=uuid.uuid4().hex,
        user_email=user_email,
        version=next_version,
        cv_source=cv_source,
        profile_json=profile_json,
        is_active=True,
    )
    session.add(profile)
    session.flush()
    return profile


def get_active_profile(session: Session, user_email: str) -> Profile | None:
    return session.exec(
        select(Profile)
        .where(Profile.user_email == user_email, Profile.is_active == True)  # noqa: E712
    ).first()


def scored_job_ids(session: Session, profile_id: str) -> set[str]:
    return set(session.exec(
        select(Score.job_id).where(Score.profile_id == profile_id)
    ).all())


def list_scored(session: Session, profile_id: str, min_score: float = 0.0):
    """Return list[(Score, Job)] for a profile, score-descending."""
    query = (
        select(Score, Job)
        .join(Job, Score.job_id == Job.id)
        .where(Score.profile_id == profile_id)
    )
    if min_score > 0:
        query = query.where(Score.overall >= min_score)
    query = query.order_by(Score.overall.desc())
    return session.exec(query).all()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_foundation.py::test_profile_versioning tests/test_foundation.py::test_score_scoping -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/storage/repo.py tests/test_foundation.py
git commit -m "feat(storage): user/profile/score repository helpers"
```

---

## Task 4: Identity resolution in config

**Files:**
- Modify: `src/jobradar/config.py` (add `UserConfig`, `resolve_user_email`)
- Test: `tests/test_foundation.py::test_resolve_user_email`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_foundation.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_foundation.py::test_resolve_user_email -v`
Expected: FAIL — `AppConfig` has no attribute `user` / no `resolve_user_email`.

- [ ] **Step 3: Add `UserConfig` and `resolve_user_email`**

In `src/jobradar/config.py`, add after the `CandidateConfig` class:

```python
class UserConfig(BaseModel):
    """Stable identity for multi-tenant scoping. Required (no silent default)."""
    email: str = ""
    display_name: str = ""
```

Add `user` to `AppConfig` (place above `candidate`):

```python
    user: UserConfig = Field(default_factory=UserConfig)
```

Add this module-level function at the end of `config.py`:

```python
def resolve_user_email(config: AppConfig, override: str | None) -> str:
    """Resolve identity: explicit override > config.user.email > error."""
    email = (override or config.user.email or "").strip()
    if not email:
        raise ValueError(
            "No user email configured. Set 'user.email' in config.yaml, "
            "pass --user <email> on the CLI, or include user_email in the skill call."
        )
    return email
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_foundation.py::test_resolve_user_email -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/config.py tests/test_foundation.py
git commit -m "feat(config): UserConfig + resolve_user_email identity resolution"
```

---

## Task 5: Pipeline scoping (profile-aware writes + skip)

**Files:**
- Modify: `src/jobradar/pipeline.py`
- Test: `tests/test_foundation.py::test_pipeline_scopes_scores`

This task rewrites the parts of `pipeline.py` that touch storage. The fetch/score/generate logic is unchanged except for what it reads/writes.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_foundation.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_foundation.py::test_pipeline_scopes_scores -v`
Expected: FAIL — `JobRadarPipeline.__init__()` takes no `user_email`.

- [ ] **Step 3: Update `pipeline.py` imports and constructor**

Change the storage import line (currently importing `ApplicationRecord, Job, PipelineRun, ScoredJobRecord`) to:

```python
from .storage.db import get_session, init_db
from .storage.models import Application, Job, PipelineRun, Score
from .storage.repo import (
    create_profile_version,
    get_active_profile,
    resolve_or_create_user,
    scored_job_ids,
)
from .sources.registry import SourceRegistry, build_registry
```

Remove the now-unused `from .utils import profile_id as _profile_id` import.

Update `__init__`:

```python
    def __init__(self, config: AppConfig, user_email: str) -> None:
        self.config = config
        self.user_email = user_email
        self.llm = LLMClient(config.llm.text)
        db_path = config.resolve_path(config.server.db_path)
        init_db(db_path)
        self._db_path = db_path
        self._registry = build_registry(config)
```

- [ ] **Step 4: Scope the run record**

In `run()`, change the `PipelineRun(...)` creation line to:

```python
            run_record = PipelineRun(
                user_email=self.user_email, mode=mode, started_at=datetime.utcnow()
            )
```

- [ ] **Step 5: Resolve user + active profile inside `_execute`**

In `_execute`, replace the Step 1 block (CV parse → profile) so that after `profile = ingest(...)` it resolves/creates the user and the active profile, reusing the active profile if its `cv_source` matches. Replace the existing Step 1 body with:

```python
        # Step 1: Parse CV → profile, then resolve the active DB profile
        cache_dir = cfg.resolve_path(cfg.server.cache_dir)
        cv_source = cfg.candidate.effective_cv()
        if cv_source.startswith("http://") or cv_source.startswith("https://"):
            cv_resolved = cv_source
        else:
            cv_resolved = str(cfg.resolve_path(cv_source))
        profile = ingest(cv_resolved, self.llm, cache_dir=cache_dir)

        resolve_or_create_user(session, self.user_email,
                               display_name=profile.personal.name)
        active = get_active_profile(session, self.user_email)
        profile_json = profile.model_dump_json()
        if active is None or active.cv_source != cv_resolved:
            active = create_profile_version(session, self.user_email,
                                            cv_resolved, profile_json)
        else:
            active.profile_json = profile_json
            session.add(active)
        session.commit()
        self._profile_id = active.id
        emit("profile_done", name=profile.personal.name)
```

- [ ] **Step 6: Update the run-record profile id**

In `run()`, after `_execute` returns, also persist the profile id. In the `try` block where `run_record.status = "done"` is set, add:

```python
                run_record.profile_id = getattr(self, "_profile_id", "")
```

- [ ] **Step 7: Scope the score-skip and writes**

In `_execute` Step 6, replace the `cand_id` / `scored_ids` block and the write loop:

```python
        # Step 6: LLM scoring (skip already-scored jobs for THIS profile)
        already = scored_job_ids(session, self._profile_id)
        unscored = [j for j in to_score if j.id not in already]
        emit("scoring_start", total=len(unscored))

        scored_jobs = score_jobs(
            unscored, profile, self.llm,
            batch_size=cfg.scoring.batch_size,
            on_batch_done=lambda s: emit("score_progress", scored=len(s)),
        )
        for sj in scored_jobs:
            session.add(Score(
                profile_id=self._profile_id, job_id=sj.job.id,
                overall=sj.score,
                skills_match=sj.breakdown.skills_match,
                seniority_fit=sj.breakdown.seniority_fit,
                location_fit=sj.breakdown.location_fit,
                language_fit=sj.breakdown.language_fit,
                visa_friendly=sj.breakdown.visa_friendly,
                growth_potential=sj.breakdown.growth_potential,
                reasoning=sj.reasoning,
                application_angle=sj.application_angle,
            ))
        session.commit()
```

- [ ] **Step 8: Scope the generated-application writes**

In `_execute` Step 7, change the `ApplicationRecord(...)` call to:

```python
            session.add(Application(
                profile_id=self._profile_id, job_id=sj.job.id,
                cv_optimized_md=cv_md, cover_letter_md=cl_md, gaps=json.dumps(gaps),
            ))
```

- [ ] **Step 9: Remove the dead `hasattr` branch (folded cleanup)**

In `_execute` Step 2, replace:

```python
        quick_limit = cfg.search.quick_max_results if hasattr(cfg.search, 'quick_max_results') else 5
```

with:

```python
        quick_limit = cfg.search.quick_max_results
```

- [ ] **Step 10: Run test to verify it passes**

Run: `python -m pytest tests/test_foundation.py::test_pipeline_scopes_scores -v`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add src/jobradar/pipeline.py tests/test_foundation.py
git commit -m "feat(pipeline): profile-scoped scoring/writes; remove dead branch"
```

---

## Task 6: API read-path scoping (jobs router)

**Files:**
- Create: `src/jobradar/api/deps.py`
- Modify: `src/jobradar/api/routers/jobs.py`
- Test: `tests/test_foundation.py::test_list_jobs_isolated`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_foundation.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_foundation.py::test_list_jobs_isolated -v`
Expected: FAIL — current `list_jobs` ignores `user_email` and joins the dropped `ScoredJobRecord` model (import error or wrong score).

- [ ] **Step 3: Create `src/jobradar/api/deps.py`**

```python
"""FastAPI dependencies — DB path resolution and user-email resolution."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Query

from ..config import resolve_user_email
from .main import get_config


def get_db_path() -> Path:
    cfg = get_config()
    return cfg.resolve_path(cfg.server.db_path)


def get_user_email(user_email: str = Query(default="")) -> str:
    try:
        return resolve_user_email(get_config(), user_email or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

- [ ] **Step 4: Rewrite `src/jobradar/api/routers/jobs.py`**

```python
"""Jobs router — query scored jobs for the active profile of a user."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlmodel import select

from ...storage.db import get_session
from ...storage.models import Job, Score
from ...storage.repo import get_active_profile, list_scored
from ..deps import get_db_path, get_user_email

router = APIRouter()


@router.get("")
def list_jobs(
    min_score: float = Query(default=0.0, ge=0, le=10),
    source: str = Query(default=""),
    status: str = Query(default=""),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    with next(get_session(db_path)) as session:
        profile = get_active_profile(session, user_email)
        if profile is None:
            return JSONResponse(content={"jobs": [], "total": 0})
        rows = list_scored(session, profile.id, min_score=min_score)

    results = []
    for score_rec, job in rows:
        if source and source not in job.source:
            continue
        if status and score_rec.status != status:
            continue
        results.append({
            "id": job.id, "title": job.title, "company": job.company,
            "location": job.location, "url": job.url, "salary": job.salary,
            "source": job.source, "date_posted": job.date_posted,
            "score": score_rec.overall,
            "breakdown": {
                "skills_match": score_rec.skills_match,
                "seniority_fit": score_rec.seniority_fit,
                "location_fit": score_rec.location_fit,
                "language_fit": score_rec.language_fit,
                "visa_friendly": score_rec.visa_friendly,
                "growth_potential": score_rec.growth_potential,
            },
            "reasoning": score_rec.reasoning,
            "application_angle": score_rec.application_angle,
            "status": score_rec.status,
            "applied": score_rec.applied,
        })

    page = results[offset: offset + limit]
    return JSONResponse(content={"jobs": page, "total": len(page)})


@router.get("/{job_id}")
def get_job(
    job_id: str,
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    with next(get_session(db_path)) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        profile = get_active_profile(session, user_email)
        score = None
        if profile is not None:
            score = session.get(Score, (profile.id, job_id))

    return JSONResponse(content={
        "id": job.id, "title": job.title, "company": job.company,
        "location": job.location, "url": job.url, "description": job.description,
        "salary": job.salary, "source": job.source, "date_posted": job.date_posted,
        "score": score.overall if score else None,
        "reasoning": score.reasoning if score else "",
        "application_angle": score.application_angle if score else "",
        "status": score.status if score else "unscored",
    })


@router.patch("/{job_id}/status")
def update_status(
    job_id: str,
    status: str = Query(...),
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    with next(get_session(db_path)) as session:
        profile = get_active_profile(session, user_email)
        if profile is None:
            raise HTTPException(status_code=404, detail="No active profile")
        record = session.get(Score, (profile.id, job_id))
        if not record:
            raise HTTPException(status_code=404, detail="Scored job not found")
        record.status = status
        if status == "applied":
            record.applied = True
            record.applied_at = datetime.now(timezone.utc)
        session.add(record)
        session.commit()

    return JSONResponse(content={"ok": True, "job_id": job_id, "status": status})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_foundation.py::test_list_jobs_isolated -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/jobradar/api/deps.py src/jobradar/api/routers/jobs.py tests/test_foundation.py
git commit -m "feat(api): profile-scoped jobs router + DI deps"
```

---

## Task 7: Apply-engine scoping + non-blocking confirm

**Files:**
- Modify: `src/jobradar/apply/engine.py`
- Test: `tests/test_foundation.py::test_apply_engine_scoped`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_foundation.py`:

```python
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
        s.add(Job(id="j1", source="bosszhipin", title="AI", url="https://zhipin/1"))
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_foundation.py::test_apply_engine_scoped -v`
Expected: FAIL — `run_apply()` has no `profile_id` parameter and queries the dropped `ScoredJobRecord`.

- [ ] **Step 3: Update `run_apply` signature and confirmation**

In `src/jobradar/apply/engine.py`, add `profile_id` as a required keyword and replace the blocking `input()` with a `confirm` callback. Change the signature:

```python
def run_apply(
    *,
    db_path: Path,
    profile_id: str,
    min_score: float = 7.5,
    dry_run: bool = False,
    daily_limit: int = 50,
    platforms: list[str] | None = None,
    confirm: Callable[[dict], bool] | None = None,
    on_result: Callable[[ApplyResult], None] | None = None,
) -> ApplySession:
```

Replace the `jobs = _load_eligible_jobs(db_path, min_score)` line with:

```python
    jobs = _load_eligible_jobs(db_path, profile_id, min_score)
```

Replace the interactive-confirm block (the `if confirm_each and not dry_run:` section) with:

```python
        # Confirmation via injected callback (caller owns any prompting/IO)
        if confirm is not None and not dry_run and not confirm(job):
            result = ApplyResult(
                job_id=job["id"], title=job["title"],
                company=job.get("company", ""), platform=job["platform"],
                status=ApplyStatus.SKIPPED, message="user skipped",
            )
            session.results.append(result)
            if on_result:
                on_result(result)
            continue
```

- [ ] **Step 4: Update `_load_eligible_jobs` to be profile-scoped**

Replace the whole `_load_eligible_jobs` function:

```python
def _load_eligible_jobs(db_path: Path, profile_id: str, min_score: float) -> list[dict]:
    """Load scored jobs for one profile, best-first, skipping already-applied."""
    from ..storage.db import get_session, init_db
    from ..storage.repo import list_scored

    init_db(db_path)
    history = ApplyHistory()
    results = []

    with next(get_session(db_path)) as session:
        for score_rec, job in list_scored(session, profile_id, min_score=min_score):
            if history.already_applied(job.id):
                continue
            if not job.url:
                continue
            results.append({
                "id": job.id, "title": job.title, "company": job.company or "",
                "location": job.location or "", "score": round(score_rec.overall, 1),
                "platform": job.source, "url": job.url,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
```

Also remove the now-unused top-of-file `import logging` only if unused elsewhere (it is still used by `logger`); keep it. Remove the unused `from .base import ... ApplyStatus` only if already imported (it is — leave as is).

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_foundation.py::test_apply_engine_scoped -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/jobradar/apply/engine.py tests/test_foundation.py
git commit -m "feat(apply): profile-scoped eligibility; callback-based confirm"
```

---

## Task 8: Report generator scoping (verify + wire)

**Files:**
- Read first: `src/jobradar/report/generator.py`, `src/jobradar/report/publisher.py`
- Modify: whichever function loads jobs from the DB to accept `profile_id`
- Test: `tests/test_foundation.py::test_report_scoped`

- [ ] **Step 1: Read the report module to find the DB-loading entry point**

Run: `sed -n '1,80p' src/jobradar/report/generator.py` and locate the function that queries `ScoredJobRecord` (it must be updated to use `repo.list_scored(session, profile_id)`); `generate_report(jobs, ...)` itself takes a list and stays unchanged (the smoke test `test_report_generates_html` confirms its signature).

- [ ] **Step 2: Write the failing test**

Append to `tests/test_foundation.py` (adjust the loader name found in Step 1 — referred to here as `load_report_jobs`):

```python
def test_report_scoped(tmp_path):
    from jobradar.report import generator
    from jobradar.storage.db import init_db, get_session
    from jobradar.storage import repo
    from jobradar.storage.models import Job, Score

    db = tmp_path / "jobradar.db"
    init_db(db)
    with next(get_session(db)) as s:
        repo.resolve_or_create_user(s, "a@x.com")
        repo.create_profile_version(s, "a@x.com", "cv.md", "{}")
        s.add(Job(id="j1", source="t", title="Eng", url="https://x/1"))
        pa = repo.get_active_profile(s, "a@x.com")
        s.add(Score(profile_id=pa.id, job_id="j1", overall=9.0))
        s.commit()
        pid = pa.id

    jobs = generator.load_report_jobs(db, pid)
    assert len(jobs) == 1 and jobs[0]["id"] == "j1"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_foundation.py::test_report_scoped -v`
Expected: FAIL — loader missing or not profile-scoped.

- [ ] **Step 4: Implement `load_report_jobs(db_path, profile_id)`**

Add to `src/jobradar/report/generator.py` (and have any existing CLI/skill report caller use it). The dict shape must match what `generate_report` expects (see `test_report_generates_html`: keys `id,title,company,location,score,source,url,date_posted,reasoning,breakdown`):

```python
def load_report_jobs(db_path, profile_id: str, min_score: float = 0.0) -> list[dict]:
    """Load a profile's scored jobs as report dicts (score-descending)."""
    from ..storage.db import get_session, init_db
    from ..storage.repo import list_scored

    init_db(db_path)
    out = []
    with next(get_session(db_path)) as session:
        for score_rec, job in list_scored(session, profile_id, min_score=min_score):
            out.append({
                "id": job.id, "title": job.title, "company": job.company,
                "location": job.location, "score": score_rec.overall,
                "source": job.source, "url": job.url, "date_posted": job.date_posted,
                "reasoning": score_rec.reasoning,
                "breakdown": {
                    "skills_match": score_rec.skills_match,
                    "seniority_fit": score_rec.seniority_fit,
                    "location_fit": score_rec.location_fit,
                    "language_fit": score_rec.language_fit,
                    "visa_friendly": score_rec.visa_friendly,
                    "growth_potential": score_rec.growth_potential,
                },
            })
    return out
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_foundation.py::test_report_scoped -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/jobradar/report/generator.py tests/test_foundation.py
git commit -m "feat(report): profile-scoped job loading"
```

---

## Task 9: CLI + skill wiring for identity

**Files:**
- Read first: `src/jobradar/interfaces/cli.py`, `src/jobradar/interfaces/skill.py`
- Modify: both, to resolve `user_email` and pass it through `JobRadarPipeline`, `run_apply`, report, and API queries
- Test: `tests/test_foundation.py::test_skill_requires_user`

- [ ] **Step 1: Map the call sites**

Run: `grep -n "JobRadarPipeline(\|run_apply(\|_load_eligible_jobs\|candidate_id\|ScoredJobRecord\|ApplicationRecord" src/jobradar/interfaces/cli.py src/jobradar/interfaces/skill.py`
Update every `JobRadarPipeline(config)` → `JobRadarPipeline(config, user_email)` and every `run_apply(...)` to pass `profile_id=` (resolve via `repo.get_active_profile(session, user_email).id`).

- [ ] **Step 2: Write the failing test**

Append to `tests/test_foundation.py`:

```python
def test_skill_requires_user(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv("JOBRADAR_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    from jobradar.interfaces.skill import run_skill
    # run_pipeline without any user_email and no config must error clearly
    out = json.loads(run_skill("run_pipeline", json.dumps({"mode": "dry-run"})))
    assert out.get("status") == "error"
    assert "user" in (out.get("error", "") + out.get("message", "")).lower()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_foundation.py::test_skill_requires_user -v`
Expected: FAIL — skill currently ignores user identity.

- [ ] **Step 4: Add `--user` to the CLI**

In `cli.py`, add a `--user` option to the `run`, `report`, and `apply` commands (Typer `Option(default="", "--user")`), and in each command body resolve it:

```python
from ..config import resolve_user_email
user_email = resolve_user_email(config, user or None)
```

Pass `user_email` into `JobRadarPipeline(config, user_email)`. For `apply`, open a session, get the active profile, and pass `profile_id=profile.id` plus a `confirm=lambda job: typer.confirm(...)` callback (replacing the engine's removed `input()`). In `init`, prompt for and persist `user.email` into `config.yaml`.

- [ ] **Step 5: Add `user_email` to skill tools**

In `skill.py`, in `run_pipeline` / `list_jobs` / `apply_jobs` / `get_report` / `get_digest`, read `user_email` from the tool args, resolve via `resolve_user_email(config, args.get("user_email"))`, and wrap pipeline/apply/report calls in `try/except ValueError` returning `{"status": "error", "error": str(exc)}`. Pass the resolved identity through (`JobRadarPipeline(config, user_email)`, `profile_id=...`).

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_foundation.py::test_skill_requires_user -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/jobradar/interfaces/cli.py src/jobradar/interfaces/skill.py tests/test_foundation.py
git commit -m "feat(interfaces): --user flag and user_email skill arg"
```

---

## Task 10: Folded cleanup — deterministic adapter IDs

**Files:**
- Modify: `src/jobradar/sources/adapters/stepstone.py`
- Test: `tests/test_foundation.py::test_stepstone_ids_deterministic`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_foundation.py`:

```python
def test_stepstone_ids_deterministic():
    from jobradar.sources.adapters import stepstone
    from bs4 import BeautifulSoup
    html = '''<a href="/stellenangebote--Senior-Engineer-12345">Senior Engineer Role</a>'''
    jobs1 = stepstone._parse_page(BeautifulSoup(html, "html.parser"))
    jobs2 = stepstone._parse_page(BeautifulSoup(html, "html.parser"))
    assert jobs1 and jobs1[0].id == jobs2[0].id          # stable within run
    assert not jobs1[0].id.startswith("stepstone-")       # uses make_id, not hash()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_foundation.py::test_stepstone_ids_deterministic -v`
Expected: FAIL — current IDs use `f"stepstone-{abs(hash(...))%10**8}"` (process-salted) and start with `stepstone-`.

- [ ] **Step 3: Replace the three ID expressions in `stepstone.py`**

Add the import at the top:

```python
from ..normalizer import make_id
```

Replace each occurrence of `id=f"stepstone-{abs(hash(url)) % 10**8}",` and `id=f"stepstone-{abs(hash(full_url)) % 10**8}",` and `id=f"stepstone-{abs(hash(job_url)) % 10**8}",` with the appropriate `make_id` call using that row's url and title, e.g.:

```python
                id=make_id("stepstone", full_url, title_text),
```
```python
            id=make_id("stepstone", job_url, title),
```
```python
        id=make_id("stepstone", url, title),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_foundation.py::test_stepstone_ids_deterministic -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/sources/adapters/stepstone.py tests/test_foundation.py
git commit -m "fix(sources): deterministic stepstone IDs via make_id"
```

---

## Task 11: Update obsolete smoke tests + CI

**Files:**
- Modify: `tests/test_smoke.py` (remove/rewrite tests referencing the dropped schema)
- Modify: `.github/workflows/ci.yml`
- Test: full suite green

- [ ] **Step 1: Identify broken smoke tests**

Run: `python -m pytest tests/test_smoke.py -q`
Expected: FAILS — `test_apply_engine_dry_run` uses `ScoredJobRecord`/`Job(candidate_id...)`/`run_apply(min_score=...)` without `profile_id`; `test_config_cv_override` is unaffected. Note every failing test.

- [ ] **Step 2: Rewrite `test_apply_engine_dry_run`**

Replace its body so it seeds via the new schema and passes `profile_id`:

```python
def test_apply_engine_dry_run(tmp_path):
    from jobradar.apply.engine import run_apply
    from jobradar.storage.db import init_db, get_session
    from jobradar.storage import repo
    from jobradar.storage.models import Job, Score

    db_path = tmp_path / "test.db"
    init_db(db_path)
    with next(get_session(db_path)) as s:
        repo.resolve_or_create_user(s, "t@x.com")
        repo.create_profile_version(s, "t@x.com", "cv.md", "{}")
        p = repo.get_active_profile(s, "t@x.com")
        s.add(Job(id="zboss1", title="AI工程师", company="字节跳动", location="北京",
                  url="https://www.zhipin.com/job/zboss1", description="AI job",
                  source="bosszhipin", date_posted="2026-03-15"))
        s.add(Score(profile_id=p.id, job_id="zboss1", overall=8.5))
        s.commit()
        pid = p.id

    result = run_apply(db_path=db_path, profile_id=pid, min_score=7.5,
                       dry_run=True, platforms=["bosszhipin"])
    assert len(result.results) == 1
    assert result.results[0].status.value == "dry_run"
```

- [ ] **Step 3: Fix any other smoke tests flagged in Step 1**

For any remaining failure caused by removed models/params, update imports/fields to the new schema (e.g. `Score` instead of `ScoredJobRecord`, no `candidate_id`). Keep `test_report_generates_html` and `test_report_score_filter` as-is — they exercise `generate_report(list, ...)` which is unchanged.

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: PASS (all tests in `test_foundation.py` and `test_smoke.py` green).

- [ ] **Step 5: Update CI to run pytest**

Read `.github/workflows/ci.yml`; replace the inline `python -c` test step with:

```yaml
      - name: Install
        run: pip install -e ".[dev]"
      - name: Test
        run: pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_smoke.py .github/workflows/ci.yml
git commit -m "test: migrate suite to new schema; CI runs pytest"
```

---

## Final verification

- [ ] Run the whole suite: `python -m pytest tests/ -v` → all green.
- [ ] Lint touched files: `ruff check src/jobradar tests` → no new errors.
- [ ] Smoke a real run path (needs an LLM key + a CV): `jobradar run --user you@x.com --cv <path> --mode dry-run` → no crash, exits cleanly.
- [ ] Confirm a fresh DB is created with six tables: `python -c "from jobradar.storage.db import init_db; init_db('/tmp/jr.db')"` then `sqlite3 /tmp/jr.db .tables` shows `application job pipeline_run profile score user`.

---

## Notes for the implementer

- **The old DB is intentionally discarded.** Do not write a migration importer. Existing users keep `config.yaml` but must add `user.email`; `jobradar.db` is recreated on first run.
- **LLM is always mocked in tests** — never require a network key to run `pytest`.
- This is **sub-project #1 of 5**. Do not pull in expiry filtering (#2), source health (#3), settings UI (#4), or broad cleanup (#5) — only the narrowly-scoped folded cleanup in Tasks 5 & 10. The spec lists what's deferred.
- If a referenced line/function has drifted from this plan, re-read the file and adapt — the design intent (profile-scoped reads/writes) governs over exact line numbers.
