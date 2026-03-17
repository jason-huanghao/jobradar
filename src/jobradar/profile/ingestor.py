"""Profile ingestor — dispatch any input source to the right reader + extractor."""

from __future__ import annotations

import logging
from pathlib import Path

from ..llm.client import LLMClient
from ..models.candidate import CandidateProfile
from .extractor import extract_profile
from .readers.file_reader import FileAndUrlReader

logger = logging.getLogger(__name__)

_reader = FileAndUrlReader()


def ingest(
    source: str,
    llm: LLMClient,
    *,
    cache_dir: Path | None = None,
    skip_if_unchanged: bool = True,
) -> CandidateProfile:
    """Read a CV from any supported source and return a CandidateProfile.

    Supported sources:
        - Local file path (.md, .txt, .pdf, .docx)
        - HTTP/HTTPS URL (HTML page, PDF, Markdown, DOCX)
        - LinkedIn: pass the path to a LinkedIn PDF export

    Args:
        source: File path string or URL string.
        llm: Configured LLMClient instance.
        cache_dir: If set, cache parsed profile by CV hash.
        skip_if_unchanged: Skip LLM call if CV hasn't changed since last parse.

    Returns:
        CandidateProfile — fully structured candidate data.
    """
    logger.info("Ingesting CV from: %s", source)
    cv_text = _reader.read(source)

    if not cv_text.strip():
        raise ValueError(f"CV source yielded no text: {source}")

    logger.info("CV text length: %d chars", len(cv_text))
    return extract_profile(cv_text, llm, cache_dir=cache_dir, skip_if_unchanged=skip_if_unchanged)
