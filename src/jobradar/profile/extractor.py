"""CV text → CandidateProfile via LLM (Jinja2 prompt template)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..llm.client import LLMClient
from ..models.candidate import CandidateProfile

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "llm" / "prompts"


def _get_schema() -> str:
    return json.dumps(CandidateProfile.model_json_schema(), indent=2)


def _render_prompt(cv_text: str) -> str:
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    tpl = env.get_template("cv_extract.jinja2")
    return tpl.render(cv_text=cv_text, schema=_get_schema())


def cv_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _recover_partial_json(raw: str) -> dict:
    """Best-effort recovery when the LLM output is truncated JSON.

    Tries three strategies:
    1. Direct parse (full valid JSON)
    2. Find the last complete top-level field and close the object
    3. Extract via regex only the fields we care most about
    """
    raw = raw.strip()

    # Strip markdown fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    # Strategy 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2: close truncated JSON by finding last complete key-value pair
    # Find the position of the last complete "key": value, pair
    # Walk backwards adding closing braces/brackets until it parses
    attempt = raw.rstrip(' \n\r\t,')
    for _ in range(20):
        for closer in [']}', ']}}}', '}}', '}', ']}}}}}']:
            try:
                return json.loads(attempt + closer)
            except json.JSONDecodeError:
                pass
        # Remove the last incomplete token and try again
        attempt = re.sub(r',?\s*"[^"]*"\s*:\s*[^,{}\[\]]*$', '', attempt)
        attempt = attempt.rstrip(' \n\r\t,')
        if not attempt:
            break

    # Strategy 3: extract minimal fields via regex fallback
    logger.warning("JSON truncation recovery: falling back to regex extraction")
    result: dict = {}

    def _extract(key: str, pattern: str) -> str:
        m = re.search(pattern, raw)
        return m.group(1) if m else ""

    # personal.name
    name = _extract("name", r'"name"\s*:\s*"([^"]*)"')
    if name:
        result["personal"] = {"name": name, "email": "", "phone": "",
                               "location": "", "linkedin": "", "github": "", "languages": []}

    # story
    story = _extract("story", r'"story"\s*:\s*"((?:[^"\\]|\\.)*)"')
    if story:
        result["story"] = story

    # target roles
    roles_m = re.search(r'"roles"\s*:\s*\[(.*?)\]', raw, re.DOTALL)
    if roles_m:
        roles = re.findall(r'"([^"]+)"', roles_m.group(1))
        result.setdefault("target", {})["roles"] = roles

    return result


def extract_profile(
    cv_text: str,
    llm: LLMClient,
    *,
    cache_dir: Path | None = None,
    skip_if_unchanged: bool = True,
) -> CandidateProfile:
    """Convert raw CV text to a CandidateProfile using LLM."""
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

    # Use higher max_tokens for CV extraction — profile JSON can be large
    original_max_tokens = llm.endpoint.max_tokens
    try:
        llm.endpoint.__dict__['max_tokens'] = max(original_max_tokens, 8192)
    except Exception:
        pass

    try:
        raw_text = llm.complete(prompt, temperature=0.1,
                                max_tokens=max(original_max_tokens, 8192))
        try:
            clean = re.sub(r'^```(?:json)?\s*', '', raw_text.strip())
            clean = re.sub(r'\s*```$', '', clean)
            raw = json.loads(clean)
        except json.JSONDecodeError:
            logger.warning("CV extraction: JSON parse failed, attempting recovery (%d chars)",
                           len(raw_text))
            raw = _recover_partial_json(raw_text)
    except Exception as e:
        logger.error("CV extraction LLM call failed: %s", e)
        raw = {}
    finally:
        try:
            llm.endpoint.__dict__['max_tokens'] = original_max_tokens
        except Exception:
            pass

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
        (cache_dir / "candidate_profile.json").write_text(
            profile.model_dump_json(indent=2))
        logger.info("Profile cached → %s", cache_dir / "candidate_profile.json")

    return profile
