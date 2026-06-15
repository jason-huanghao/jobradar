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


class UserSettings(SQLModel, table=True):
    """Per-user LLM endpoint selection. Keyed by user.email.

    Stores the *selection* (provider/model/base_url + the env-var name holding the
    key) — never the secret key value, which stays in the environment/.env."""

    __tablename__ = "user_settings"

    user_email: str = Field(primary_key=True, foreign_key="user.email")
    provider: str = ""          # catalog id, or "custom"
    model: str = ""
    base_url: str = ""
    api_key_env: str = ""
    updated_at: datetime = Field(default_factory=_utcnow)


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
