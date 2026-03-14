"""CV text → CandidateProfile via LLM (Jinja2 prompt template)."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..llm.client import LLMClient
from ..models.candidate import CandidateProfile

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "llm" / "prompts"


def _get_schema() -> str:
    """Return the CandidateProfile JSON schema as a string."""
    return json.dumps(CandidateProfile.model_json_schema(), indent=2)


def _render_prompt(cv_text: str) -> str:
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    tpl = env.get_template("cv_extract.jinja2")
    return tpl.render(cv_text=cv_text, schema=_get_schema())


def cv_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def extract_profile(
    cv_text: str,
    llm: LLMClient,
    *,
    cache_dir: Path | None = None,
    skip_if_unchanged: bool = True,
) -> CandidateProfile:
    """Convert raw CV text to a CandidateProfile using LLM.

    Uses a Jinja2 prompt template (llm/prompts/cv_extract.jinja2).
    Caches the result by CV text hash to avoid re-parsing unchanged CVs.
    """
    current_hash = cv_hash(cv_text)

    if cache_dir and skip_if_unchanged:
        hash_file = cache_dir / "cv_hash.txt"
        profile_file = cache_dir / "candidate_profile.json"
        if hash_file.exists() and profile_file.exists():
            if hash_file.read_text().strip() == current_hash:
                logger.info("CV unchanged — loading cached profile")
                return CandidateProfile(**json.loads(profile_file.read_text()))

    prompt = _render_prompt(cv_text)
    logger.info("Extracting profile via LLM (%s)…", llm.endpoint.model)

    raw = llm.complete_auto(prompt, temperature=0.1)
    profile = CandidateProfile(**(raw if isinstance(raw, dict) else {}))

    # Warn on obviously incomplete extractions
    for field, val in [("name", profile.personal.name),
                       ("experience", profile.experience),
                       ("technical skills", profile.skills.technical)]:
        if not val:
            logger.warning("Profile extraction: '%s' is empty — check CV quality", field)

    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "cv_hash.txt").write_text(current_hash)
        (cache_dir / "candidate_profile.json").write_text(profile.model_dump_json(indent=2))
        logger.info("Profile cached → %s", cache_dir / "candidate_profile.json")

    return profile
