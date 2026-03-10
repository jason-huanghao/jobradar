"""CV → structured JSON CandidateProfile via LLM.

Supports .md, .txt, .pdf, .docx, .doc input formats.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from .cv_reader import detect_cv_format, read_cv_auto, read_cv_file
from .llm_client import LLMClient
from .models import CandidateProfile

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a CV parsing expert. Read the following CV (may be from Markdown, PDF, or Word) and extract \
structured information into the JSON schema below.

RULES:
- If information is not present in the CV, use empty string "" or empty array []
- Never invent information not in the CV
- For "story": write a 150-300 word narrative summary of the candidate
- For "roles_de": translate the target roles into German job titles
- For "visa_needed": infer from nationality + location (non-EU in Germany = true)

Output ONLY valid JSON. No markdown fences, no explanation."""


def _load_schema() -> str:
    schema_path = Path(__file__).parent.parent / "schemas" / "candidate_profile.schema.json"
    return schema_path.read_text()


def _cv_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def read_cv(cv_path: Path | str) -> str:
    """Read a CV from a local file path or a remote URL.

    Accepts:
        Path / str  — local file (.md, .pdf, .docx, .txt)
        str         — http(s):// URL (HTML, PDF, Markdown, DOCX)

    Delegates to cv_reader.read_cv_auto() for format-aware extraction.
    Kept as `read_cv` for backward compatibility with existing call sites.
    """
    source = str(cv_path)
    if source.startswith("http://") or source.startswith("https://"):
        logger.info("Reading CV from URL: %s", source)
    else:
        fmt = detect_cv_format(Path(source))
        logger.info("Reading CV: %s (%s)", Path(source).name, fmt)
    return read_cv_auto(source)


def parse_cv_to_profile(
    cv_text: str,
    llm: LLMClient,
    *,
    cache_dir: Path | None = None,
    skip_if_unchanged: bool = True,
) -> CandidateProfile:
    """Convert Markdown CV text to a CandidateProfile using LLM.

    If cache_dir is provided, caches the result and skips re-parsing
    if the CV content hash hasn't changed.
    """
    current_hash = _cv_hash(cv_text)

    # Check cache
    if cache_dir and skip_if_unchanged:
        hash_file = cache_dir / "cv_hash.txt"
        profile_file = cache_dir / "candidate_profile.json"
        if hash_file.exists() and profile_file.exists():
            cached_hash = hash_file.read_text().strip()
            if cached_hash == current_hash:
                logger.info("CV unchanged (hash match) — loading cached profile")
                raw = json.loads(profile_file.read_text())
                return CandidateProfile(**raw)

    # Build prompt
    schema_text = _load_schema()
    prompt = f"JSON SCHEMA:\n{schema_text}\n\nMARKDOWN CV:\n{cv_text}"

    logger.info("Parsing CV via LLM (%s)...", llm.endpoint.model)
    # Volcengine Ark doesn't support json_object response_format — go straight to structured
    if llm.endpoint.provider == "volcengine":
        raw_json = llm.complete_structured(prompt, system=_SYSTEM_PROMPT, temperature=0.1)
    else:
        try:
            raw_json = llm.complete_json(prompt, system=_SYSTEM_PROMPT, temperature=0.1)
        except Exception:
            logger.warning("json_mode failed, retrying with structured output")
            raw_json = llm.complete_structured(prompt, system=_SYSTEM_PROMPT, temperature=0.1)

    profile = CandidateProfile(**raw_json)

    # Validate critical fields
    warnings = []
    if not profile.personal.name:
        warnings.append("name is empty")
    if not profile.experience:
        warnings.append("no experience entries found")
    if not profile.skills.technical:
        warnings.append("no technical skills found")
    for w in warnings:
        logger.warning("CV parse warning: %s", w)

    # Save cache
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "cv_hash.txt").write_text(current_hash)
        (cache_dir / "candidate_profile.json").write_text(
            profile.model_dump_json(indent=2)
        )
        logger.info("Cached parsed profile to %s", cache_dir / "candidate_profile.json")

    return profile
