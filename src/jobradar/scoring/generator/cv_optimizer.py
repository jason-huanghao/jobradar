"""CV optimizer — rewrite CV sections to match a specific job."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ...llm.client import LLMClient
from ...models.candidate import CandidateProfile
from ...models.job import RawJob

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "llm" / "prompts"


def optimize_cv(
    job: RawJob,
    profile: CandidateProfile,
    llm: LLMClient,
) -> tuple[str, list[str]]:
    """Generate a tailored CV summary + skills section for a specific job.

    Returns:
        (full_cv_md, gaps)
        full_cv_md: Markdown string combining rewritten summary + skills section
        gaps:       List of honest gaps the candidate has for this role
    """
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    template = env.get_template("cv_optimize.jinja2")

    profile_summary = _build_summary(profile)
    prompt = template.render(profile_summary=profile_summary, job=job)

    try:
        raw = llm.complete_auto(prompt, temperature=0.3)
        result = raw if isinstance(raw, dict) else {}
    except Exception as exc:
        logger.error("CV optimizer LLM call failed: %s", exc)
        return "", []

    summary = result.get("cv_summary", "")
    skills = result.get("skills_section", "")
    gaps = result.get("gaps", [])

    md = f"## Professional Summary\n\n{summary}\n\n## Skills\n\n{skills}"
    return md, gaps if isinstance(gaps, list) else []


def _build_summary(profile: CandidateProfile) -> str:
    parts = [
        f"Name: {profile.personal.name}",
        f"Seniority: {profile.seniority_level or 'unknown'}",
    ]
    if profile.experience:
        exp_lines = [
            f"  - {e.title} at {e.company} ({e.start_date}–{e.end_date}): {e.description[:200]}"
            for e in profile.experience[:4]
        ]
        parts.append("Experience:\n" + "\n".join(exp_lines))
    if profile.skills.technical:
        parts.append(f"Technical skills: {', '.join(profile.skills.technical)}")
    if profile.skills.domains:
        parts.append(f"Domains: {', '.join(profile.skills.domains)}")
    if profile.education:
        edu = profile.education[0]
        parts.append(f"Education: {edu.degree} in {edu.field} from {edu.institution}")
    if profile.inferred_strengths:
        parts.append(f"Key strengths: {', '.join(profile.inferred_strengths)}")
    return "\n".join(parts)
