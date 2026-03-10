"""Pydantic models for CandidateProfile, RawJob, ScoredJob, SearchQuery."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Candidate Profile ──────────────────────────────────────────────


class Language(BaseModel):
    language: str = ""
    level: str = ""


class Personal(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    website_url: str = ""
    nationality: str = ""
    languages: list[Language] = Field(default_factory=list)


class Target(BaseModel):
    roles: list[str] = Field(default_factory=list)
    roles_de: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    work_mode: Literal["remote", "hybrid", "onsite", "flexible", ""] = ""
    salary_expectation: str = ""
    visa_needed: bool = False
    earliest_start: str = ""
    industries: list[str] = Field(default_factory=list)
    dealbreakers: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str = ""
    field: str = ""
    institution: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    thesis_topic: str = ""
    gpa: str = ""


class Experience(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class Skills(BaseModel):
    technical: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class Publication(BaseModel):
    title: str = ""
    venue: str = ""
    year: str = ""
    url: str = ""


class CandidateProfile(BaseModel):
    """Structured candidate profile extracted from Markdown CV by LLM."""

    personal: Personal = Field(default_factory=Personal)
    target: Target = Field(default_factory=Target)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    publications: list[Publication] = Field(default_factory=list)
    story: str = ""


# ── Job Models ─────────────────────────────────────────────────────


class RawJob(BaseModel):
    """A job listing scraped from any source, before scoring."""

    id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    url: str = ""
    description: str = ""
    source: str = ""  # arbeitsagentur, indeed, google, stepstone, linkedin, xing
    date_posted: str = ""
    job_type: str = ""  # fulltime, parttime, contract
    salary: str = ""
    remote: bool | None = None
    raw_data: dict = Field(default_factory=dict)  # source-specific extras
    first_seen_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @property
    def dedup_key(self) -> str:
        """Key for URL-based deduplication (normalized URL)."""
        return self.url.strip().lower() if self.url else f"{self.title}|{self.company}".lower()


class ScoreBreakdown(BaseModel):
    skills_match: float = 0.0
    seniority_fit: float = 0.0
    location_fit: float = 0.0
    language_fit: float = 0.0
    visa_friendly: float = 0.0
    growth_potential: float = 0.0


class ScoredJob(BaseModel):
    """A job listing with LLM-generated match score."""

    job: RawJob
    score: float = 0.0  # overall 1-10
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    reasoning: str = ""
    application_angle: str = ""
    scored_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    # Application tracking — set via JobPool.mark_applied(), never written directly
    applied: bool = False
    applied_at: str = ""

    @property
    def avg_dimension_score(self) -> float:
        """Average of all 6 scoring dimensions."""
        b = self.breakdown
        vals = [b.skills_match, b.seniority_fit, b.location_fit,
                b.language_fit, b.visa_friendly, b.growth_potential]
        return sum(vals) / len(vals) if vals else 0.0


# ── Search Query ───────────────────────────────────────────────────


class SearchQuery(BaseModel):
    """A platform-specific search query generated from the candidate profile."""

    keyword: str
    location: str = ""
    source: str = ""  # which platform
    language: str = "en"  # en or de
    extra: dict = Field(default_factory=dict)  # source-specific params
