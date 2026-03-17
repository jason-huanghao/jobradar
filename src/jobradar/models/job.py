"""Shared Pydantic models — job listings."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class RawJob(BaseModel):
    """A job listing scraped from any source, before scoring."""

    id: str = ""                  # sha256(source + url) set by normalizer
    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    description: str = ""
    source: str = ""              # arbeitsagentur | jobspy:indeed | bosszhipin …
    date_posted: str = ""
    job_type: str = "fulltime"
    salary: str = ""
    remote: bool | None = None
    raw_extra: dict = Field(default_factory=dict)
    first_seen_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ScoreBreakdown(BaseModel):
    skills_match: float = 0.0
    seniority_fit: float = 0.0
    location_fit: float = 0.0
    language_fit: float = 0.0
    visa_friendly: float = 0.0
    growth_potential: float = 0.0


class ScoredJob(BaseModel):
    """A job listing with LLM-generated match score and optional generated docs."""

    job: RawJob
    score: float = 0.0
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    reasoning: str = ""
    application_angle: str = ""
    scored_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    # Application tracking
    applied: bool = False
    applied_at: str = ""
    # Generated documents (populated by generator module)
    cv_optimized_md: str = ""
    cover_letter_md: str = ""

    @property
    def avg_dimension_score(self) -> float:
        b = self.breakdown
        vals = [b.skills_match, b.seniority_fit, b.location_fit,
                b.language_fit, b.visa_friendly, b.growth_potential]
        return sum(vals) / len(vals) if vals else 0.0


class SearchQuery(BaseModel):
    """A platform-specific search query generated from the candidate profile."""

    keyword: str
    location: str = ""
    source: str = ""
    language: str = "en"          # en | de | zh
    extra: dict = Field(default_factory=dict)
