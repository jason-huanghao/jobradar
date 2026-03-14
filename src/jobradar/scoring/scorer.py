"""LLM-based job scorer — batched, Jinja2-templated."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..llm.client import LLMClient
from ..models.candidate import CandidateProfile
from ..models.job import RawJob, ScoreBreakdown, ScoredJob

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "llm" / "prompts"


def _profile_summary(profile: CandidateProfile) -> str:
    parts = [f"Name: {profile.personal.name}"]
    if profile.story:
        parts.append(f"Summary: {profile.story}")
    if profile.target.roles:
        parts.append(f"Target roles: {', '.join(profile.target.roles)}")
    if profile.target.locations:
        parts.append(f"Preferred locations: {', '.join(profile.target.locations)}")
    if profile.personal.languages:
        langs = [f"{l.language} ({l.level})" for l in profile.personal.languages]
        parts.append(f"Languages: {', '.join(langs)}")
    if profile.skills.technical:
        parts.append(f"Technical skills: {', '.join(profile.skills.technical[:15])}")
    if profile.skills.domains:
        parts.append(f"Domains: {', '.join(profile.skills.domains)}")
    parts.append(f"Visa needed: {profile.target.visa_needed}")
    if profile.target.dealbreakers:
        parts.append(f"Dealbreakers: {', '.join(profile.target.dealbreakers)}")
    if profile.inferred_strengths:
        parts.append(f"Strengths: {', '.join(profile.inferred_strengths)}")
    return "\n".join(parts)


def score_jobs(
    jobs: list[RawJob],
    profile: CandidateProfile,
    llm: LLMClient,
    batch_size: int = 5,
    on_batch_done: callable | None = None,
    feedback_context: str = "",
) -> list[ScoredJob]:
    """Score all jobs in batches. Calls on_batch_done(scored_so_far) after each batch."""
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    template = env.get_template("job_score.jinja2")

    summary = _profile_summary(profile)
    if feedback_context:
        summary += f"\n\nUser feedback context:\n{feedback_context}"

    scored: list[ScoredJob] = []
    total = len(jobs)
    n_batches = (total + batch_size - 1) // batch_size

    for i in range(0, total, batch_size):
        batch = jobs[i: i + batch_size]
        batch_num = i // batch_size + 1
        logger.info("Scoring batch %d/%d (%d jobs)…", batch_num, n_batches, len(batch))

        results = _score_batch(batch, summary, template, llm)
        scored.extend(results)

        if on_batch_done:
            try:
                on_batch_done(scored)
            except Exception as exc:
                logger.warning("Checkpoint callback failed: %s", exc)

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


def _score_batch(
    jobs: list[RawJob],
    profile_summary: str,
    template,
    llm: LLMClient,
) -> list[ScoredJob]:
    prompt = template.render(
        profile_summary=profile_summary,
        jobs=jobs,
        n_jobs=len(jobs),
    )
    try:
        raw = llm.complete_auto(prompt, temperature=0.2)
        results = raw if isinstance(raw, list) else raw.get("jobs", raw.get("results", [raw]))
    except Exception as exc:
        logger.error("Scoring batch LLM call failed: %s", exc)
        return [ScoredJob(job=j, score=0.0, reasoning="Scoring failed") for j in jobs]

    scored: list[ScoredJob] = []
    for idx, job in enumerate(jobs):
        r = results[idx] if idx < len(results) else {}
        try:
            breakdown = ScoreBreakdown(**r.get("breakdown", {}))
        except Exception:
            breakdown = ScoreBreakdown()
        scored.append(ScoredJob(
            job=job,
            score=float(r.get("score", 0)),
            breakdown=breakdown,
            reasoning=r.get("reasoning", ""),
            application_angle=r.get("application_angle", ""),
        ))
    return scored
