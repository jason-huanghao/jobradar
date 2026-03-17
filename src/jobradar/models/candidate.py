"""Shared Pydantic models — candidate profile."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Language(BaseModel):
    language: str = ""
    level: str = ""  # native, fluent, professional, conversational, basic


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
    roles_cn: list[str] = Field(default_factory=list)
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
    """Structured candidate profile extracted from CV by LLM.

    Designed to be serialized to JSON and stored in the DB.
    All fields default to empty so partial extractions are safe.
    """
    personal: Personal = Field(default_factory=Personal)
    target: Target = Field(default_factory=Target)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    publications: list[Publication] = Field(default_factory=list)
    # LLM-inferred fields (headhunter perspective)
    story: str = ""                        # 150-300 word positioning narrative
    positioning_summary: str = ""          # how a headhunter would pitch this candidate
    inferred_strengths: list[str] = Field(default_factory=list)
    likely_gaps: list[str] = Field(default_factory=list)
    seniority_level: str = ""              # junior / mid / senior / lead / principal
