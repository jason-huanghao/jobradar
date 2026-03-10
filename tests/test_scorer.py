"""Tests for the scoring engine."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.models import CandidateProfile, RawJob, ScoredJob
from src.scorer import score_jobs

FIXTURES = Path(__file__).parent / "fixtures"


def _load_profile() -> CandidateProfile:
    raw = json.loads((FIXTURES / "sample_profile.json").read_text())
    return CandidateProfile(**raw)


def _load_jobs() -> list[RawJob]:
    raw = json.loads((FIXTURES / "sample_jobs.json").read_text())
    return [RawJob(**j) for j in raw]


def test_score_jobs_returns_scored_list():
    """Test that scoring produces ScoredJob objects with valid scores."""
    profile = _load_profile()
    jobs = _load_jobs()

    # Mock LLM to return scoring results
    mock_llm = MagicMock()
    mock_llm.endpoint.model = "test-model"
    mock_llm.complete_json.return_value = [
        {
            "score": 8.5,
            "breakdown": {
                "skills_match": 9,
                "seniority_fit": 8,
                "location_fit": 7,
                "language_fit": 8,
                "visa_friendly": 7,
                "growth_potential": 9,
            },
            "reasoning": "Strong match for AI Engineer role.",
            "application_angle": "Emphasize KG and RAG experience.",
        },
        {
            "score": 9.0,
            "breakdown": {
                "skills_match": 10,
                "seniority_fit": 9,
                "location_fit": 10,
                "language_fit": 8,
                "visa_friendly": 7,
                "growth_potential": 9,
            },
            "reasoning": "Excellent match for causal ML research.",
            "application_angle": "Highlight PhD research and publications.",
        },
        {
            "score": 2.0,
            "breakdown": {
                "skills_match": 2,
                "seniority_fit": 3,
                "location_fit": 4,
                "language_fit": 8,
                "visa_friendly": 7,
                "growth_potential": 2,
            },
            "reasoning": "Frontend role doesn't match AI background.",
            "application_angle": "Not recommended.",
        },
    ]

    scored = score_jobs(jobs, profile, "mock cv text", mock_llm, batch_size=5)

    assert len(scored) == 3
    assert all(isinstance(s, ScoredJob) for s in scored)

    # Should be sorted by score descending
    assert scored[0].score >= scored[1].score >= scored[2].score

    # Top match should be the ML Researcher
    assert scored[0].score == 9.0
    assert scored[0].job.title == "Machine Learning Researcher"

    # Low match should be frontend
    assert scored[-1].score == 2.0
    assert scored[-1].job.title == "Frontend Developer"


def test_score_jobs_handles_llm_failure():
    """Test graceful handling when LLM fails."""
    profile = _load_profile()
    jobs = _load_jobs()[:1]

    mock_llm = MagicMock()
    mock_llm.endpoint.model = "test-model"
    mock_llm.complete_json.side_effect = Exception("API error")
    mock_llm.complete_structured.side_effect = Exception("API error")

    scored = score_jobs(jobs, profile, "mock cv text", mock_llm, batch_size=5)

    assert len(scored) == 1
    assert scored[0].score == 0.0
    assert "failed" in scored[0].reasoning.lower()
