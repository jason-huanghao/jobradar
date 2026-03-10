"""LLM-based job scoring engine: score candidate–job fit on multiple dimensions."""

from __future__ import annotations

import json
import logging

from .llm_client import LLMClient
from .models import CandidateProfile, RawJob, ScoreBreakdown, ScoredJob

logger = logging.getLogger(__name__)

_SCORER_SYSTEM = """You are a job matching expert. Score how well the candidate matches each job.

For EACH job, provide a JSON object with:
- "score": overall fit 1-10 (10 = perfect match)
- "breakdown": object with these dimensions (each 1-10):
    - skills_match: technical skills overlap
    - seniority_fit: experience level match
    - location_fit: location compatibility
    - language_fit: language requirements met
    - visa_friendly: visa/work permit feasibility
    - growth_potential: career growth alignment
- "reasoning": 2-3 sentence explanation of the score
- "application_angle": 1-2 sentences on what to emphasize in a cover letter

Output ONLY a JSON array of objects (one per job). No markdown fences, no explanation."""


def score_jobs(
    jobs: list[RawJob],
    profile: CandidateProfile,
    cv_text: str,
    llm: LLMClient,
    batch_size: int = 5,
    on_batch_done: callable = None,
    feedback_summary: str = "",
) -> list[ScoredJob]:
    """Score a list of jobs against the candidate profile.

    Processes in batches. Calls on_batch_done(scored_so_far) after each batch
    for checkpoint saving.
    """
    scored: list[ScoredJob] = []
    profile_summary = _build_profile_summary(profile, cv_text)
    if feedback_summary:
        profile_summary += feedback_summary
    total = len(jobs)
    total_batches = (total + batch_size - 1) // batch_size

    for i in range(0, total, batch_size):
        batch = jobs[i : i + batch_size]
        batch_num = i // batch_size + 1
        logger.info("Scoring batch %d/%d (jobs %d-%d / %d)",
                    batch_num, total_batches, i + 1, i + len(batch), total)

        batch_results = _score_batch(batch, profile_summary, llm)
        scored.extend(batch_results)

        # Checkpoint callback
        if on_batch_done:
            try:
                on_batch_done(scored)
            except Exception as e:
                logger.warning("Checkpoint save failed: %s", e)

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def _build_profile_summary(profile: CandidateProfile, cv_text: str) -> str:
    """Build a compact profile summary for the scoring prompt."""
    parts = [f"# Candidate: {profile.personal.name}"]

    if profile.story:
        parts.append(f"\n## Summary\n{profile.story}")

    if profile.target.roles:
        parts.append(f"\n## Target Roles: {', '.join(profile.target.roles)}")

    if profile.target.locations:
        parts.append(f"## Preferred Locations: {', '.join(profile.target.locations)}")

    if profile.personal.languages:
        langs = [f"{l.language} ({l.level})" for l in profile.personal.languages]
        parts.append(f"## Languages: {', '.join(langs)}")

    if profile.skills.technical:
        parts.append(f"## Technical Skills: {', '.join(profile.skills.technical[:15])}")

    if profile.skills.domains:
        parts.append(f"## Domains: {', '.join(profile.skills.domains)}")

    parts.append(f"\n## Visa Needed: {profile.target.visa_needed}")

    if profile.target.dealbreakers:
        parts.append(f"## Dealbreakers: {', '.join(profile.target.dealbreakers)}")

    return "\n".join(parts)


def _score_batch(
    jobs: list[RawJob],
    profile_summary: str,
    llm: LLMClient,
) -> list[ScoredJob]:
    """Score a batch of jobs in a single LLM call."""
    jobs_text = ""
    for idx, job in enumerate(jobs):
        desc_truncated = job.description[:1500] if job.description else "(no description)"
        jobs_text += f"""
---
JOB {idx + 1}:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Type: {job.job_type}
Remote: {job.remote}
Salary: {job.salary}
Description:
{desc_truncated}
"""

    prompt = f"""CANDIDATE PROFILE:
{profile_summary}

JOBS TO SCORE:
{jobs_text}

Score each job. Return a JSON array with {len(jobs)} objects."""

    try:
        # Volcengine Ark doesn't support json_object response_format
        if llm.endpoint.provider == "volcengine":
            raw = llm.complete_structured(prompt, system=_SCORER_SYSTEM, temperature=0.2)
        else:
            raw = llm.complete_json(prompt, system=_SCORER_SYSTEM, temperature=0.2)
        results = raw if isinstance(raw, list) else raw.get("jobs", raw.get("results", [raw]))
    except Exception as e:
        logger.warning("Scoring LLM call failed, retrying without json_mode: %s", e)
        try:
            raw = llm.complete_structured(prompt, system=_SCORER_SYSTEM, temperature=0.2)
            results = raw if isinstance(raw, list) else raw.get("jobs", raw.get("results", [raw]))
        except Exception as e2:
            logger.error("Scoring batch failed: %s", e2)
            return [ScoredJob(job=j, score=0.0, reasoning="Scoring failed") for j in jobs]

    scored: list[ScoredJob] = []
    for idx, job in enumerate(jobs):
        if idx < len(results):
            r = results[idx]
            try:
                breakdown = ScoreBreakdown(**r.get("breakdown", {}))
            except Exception:
                breakdown = ScoreBreakdown()

            scored.append(
                ScoredJob(
                    job=job,
                    score=float(r.get("score", 0)),
                    breakdown=breakdown,
                    reasoning=r.get("reasoning", ""),
                    application_angle=r.get("application_angle", ""),
                )
            )
        else:
            scored.append(ScoredJob(job=job, score=0.0, reasoning="No score returned"))

    return scored
