"""Cover letter generator."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ...llm.client import LLMClient
from ...models.candidate import CandidateProfile
from ...models.job import ScoredJob

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "llm" / "prompts"


def generate_cover_letter(
    scored_job: ScoredJob,
    profile: CandidateProfile,
    llm: LLMClient,
) -> str:
    """Generate a tailored cover letter for a specific job.

    Returns Markdown string.
    """
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    template = env.get_template("cover_letter.jinja2")

    profile_summary = _build_summary(profile)
    prompt = template.render(
        profile=profile,
        profile_summary=profile_summary,
        job=scored_job.job,
        application_angle=scored_job.application_angle,
    )

    try:
        return llm.complete(prompt, temperature=0.4)
    except Exception as exc:
        logger.error("Cover letter generation failed: %s", exc)
        return ""


def _build_summary(profile: CandidateProfile) -> str:
    parts = [f"Candidate: {profile.personal.name}"]
    if profile.story:
        parts.append(profile.story)
    if profile.skills.technical:
        parts.append(f"Technical: {', '.join(profile.skills.technical[:10])}")
    if profile.target.roles:
        parts.append(f"Target roles: {', '.join(profile.target.roles)}")
    return "\n".join(parts)
