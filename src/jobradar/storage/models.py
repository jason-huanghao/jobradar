"""SQLModel table definitions — single source of truth for DB schema."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Candidate(SQLModel, table=True):
    """One row per parsed candidate profile version."""

    id: str = Field(primary_key=True)        # sha256(cv_source_path or cv_text)
    source_path: str = ""                    # original file path or URL
    profile_json: str = Field(default="{}")  # CandidateProfile serialized
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Job(SQLModel, table=True):
    """Deduplicated raw job listing."""

    id: str = Field(primary_key=True)        # sha256(source + url)
    source: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    url: str = ""
    date_posted: str = ""
    job_type: str = "fulltime"
    salary: str = ""
    remote: Optional[bool] = None
    raw_extra: str = Field(default="{}")     # JSON blob
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class ScoredJobRecord(SQLModel, table=True):
    """LLM score for a specific candidate–job pair."""

    __tablename__ = "scored_job"

    job_id: str = Field(primary_key=True, foreign_key="job.id")
    candidate_id: str = Field(primary_key=True, foreign_key="candidate.id")
    overall: float = 0.0
    skills_match: float = 0.0
    seniority_fit: float = 0.0
    location_fit: float = 0.0
    language_fit: float = 0.0
    visa_friendly: float = 0.0
    growth_potential: float = 0.0
    reasoning: str = ""
    application_angle: str = ""
    scored_at: datetime = Field(default_factory=datetime.utcnow)
    # Tracking
    applied: bool = False
    applied_at: Optional[datetime] = None
    status: str = "new"      # new | interested | applied | rejected | interview | offer


class ApplicationRecord(SQLModel, table=True):
    """Generated CV + cover letter for a specific candidate–job pair."""

    __tablename__ = "application"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(foreign_key="job.id")
    candidate_id: str = Field(foreign_key="candidate.id")
    cv_optimized_md: str = ""
    cover_letter_md: str = ""
    gaps: str = Field(default="[]")  # JSON list of identified gaps
    status: str = "draft"            # draft | sent | rejected | interview
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackRecord(SQLModel, table=True):
    """User signals — liked/disliked companies or roles."""

    __tablename__ = "feedback"

    id: Optional[int] = Field(default=None, primary_key=True)
    signal: str = ""         # liked | disliked | applied | ignored | blocked
    company: Optional[str] = None
    role: Optional[str] = None
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineRun(SQLModel, table=True):
    """Record of each pipeline execution."""

    __tablename__ = "pipeline_run"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: str = ""
    mode: str = "full"       # full | quick | score-only | dry-run
    sources_run: str = Field(default="[]")  # JSON list
    jobs_fetched: int = 0
    jobs_new: int = 0
    jobs_scored: int = 0
    jobs_generated: int = 0
    status: str = "running"  # running | done | failed
    error: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
