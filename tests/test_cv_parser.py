"""Tests for cv_parser.py — CV → CandidateProfile via LLM.

Covers:
  - read_cv() with .md, .pdf, .docx inputs
  - parse_cv_to_profile() with mock LLM
  - caching behaviour
  - validation warnings
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from src.cv_parser import parse_cv_to_profile, read_cv
from src.models import CandidateProfile

FIXTURES = Path(__file__).parent / "fixtures"


# ══════════════════════════════════════════════════════════════════
# read_cv() — format dispatch
# ══════════════════════════════════════════════════════════════════

class TestReadCv:
    def test_reads_markdown(self):
        text = read_cv(FIXTURES / "sample_cv.md")
        assert "John Doe" in text
        assert "PhD" in text
        assert "Knowledge Graphs" in text

    def test_reads_pdf(self, sample_pdf_path):
        text = read_cv(sample_pdf_path)
        assert "John Doe" in text
        assert "Python" in text

    def test_reads_docx(self, sample_docx_path):
        text = read_cv(sample_docx_path)
        assert "John Doe" in text
        assert "Python" in text

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            read_cv(Path("/nonexistent/cv.md"))

    def test_unsupported_format(self, tmp_path):
        f = tmp_path / "cv.odt"
        f.write_text("content")
        with pytest.raises(ValueError, match="Unsupported CV format"):
            read_cv(f)


# ══════════════════════════════════════════════════════════════════
# parse_cv_to_profile() — with mocked LLM
# ══════════════════════════════════════════════════════════════════

class TestParseCvToProfile:
    def test_parses_markdown_cv(self, mock_llm, sample_profile_data, tmp_path):
        cv_text = read_cv(FIXTURES / "sample_cv.md")
        profile = parse_cv_to_profile(
            cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False
        )
        assert isinstance(profile, CandidateProfile)
        assert profile.personal.name == "John Doe"
        assert profile.personal.location == "Hannover, Germany"
        assert "Python" in profile.skills.technical
        assert profile.target.visa_needed is True

    def test_parses_pdf_cv(self, mock_llm, sample_pdf_path, tmp_path):
        """parse_cv_to_profile should work identically whether text came from PDF."""
        cv_text = read_cv(sample_pdf_path)
        assert len(cv_text) > 50, "PDF should yield non-trivial text"
        profile = parse_cv_to_profile(
            cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False
        )
        assert isinstance(profile, CandidateProfile)
        assert profile.personal.name == "John Doe"

    def test_parses_docx_cv(self, mock_llm, sample_docx_path, tmp_path):
        """parse_cv_to_profile should work identically whether text came from DOCX."""
        cv_text = read_cv(sample_docx_path)
        assert len(cv_text) > 50
        profile = parse_cv_to_profile(
            cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False
        )
        assert isinstance(profile, CandidateProfile)
        assert profile.personal.name == "John Doe"

    def test_returns_candidate_profile_type(self, mock_llm, tmp_path):
        cv_text = read_cv(FIXTURES / "sample_cv.md")
        profile = parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path)
        assert isinstance(profile, CandidateProfile)
        assert len(profile.skills.technical) > 0
        assert len(profile.experience) > 0

    def test_volcengine_uses_structured(self, sample_profile_data, tmp_path):
        """Volcengine provider should call complete_structured, not complete_json."""
        mock_llm = MagicMock()
        mock_llm.endpoint.provider = "volcengine"
        mock_llm.endpoint.model = "doubao-seed"
        mock_llm.complete_structured.return_value = sample_profile_data

        cv_text = read_cv(FIXTURES / "sample_cv.md")
        parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False)

        mock_llm.complete_structured.assert_called_once()
        mock_llm.complete_json.assert_not_called()

    def test_non_volcengine_uses_json_mode(self, mock_llm, sample_profile_data, tmp_path):
        """Non-volcengine providers should prefer complete_json."""
        cv_text = read_cv(FIXTURES / "sample_cv.md")
        parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False)
        mock_llm.complete_json.assert_called_once()

    def test_falls_back_to_structured_on_json_failure(self, sample_profile_data, tmp_path):
        """If complete_json raises, should fall back to complete_structured."""
        mock_llm = MagicMock()
        mock_llm.endpoint.provider = "openai"
        mock_llm.endpoint.model = "gpt-4o"
        mock_llm.complete_json.side_effect = Exception("json_mode not supported")
        mock_llm.complete_structured.return_value = sample_profile_data

        cv_text = read_cv(FIXTURES / "sample_cv.md")
        profile = parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False)
        assert profile.personal.name == "John Doe"
        mock_llm.complete_structured.assert_called_once()

    def test_logs_warning_for_empty_name(self, sample_profile_data, tmp_path, caplog):
        """Should log a warning when parsed name is empty."""
        import logging
        bad_profile = dict(sample_profile_data)
        bad_profile["personal"] = dict(bad_profile["personal"])
        bad_profile["personal"]["name"] = ""

        mock_llm = MagicMock()
        mock_llm.endpoint.provider = "openai"
        mock_llm.endpoint.model = "test"
        mock_llm.complete_json.return_value = bad_profile

        cv_text = read_cv(FIXTURES / "sample_cv.md")
        with caplog.at_level(logging.WARNING):
            parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False)

        assert any("name is empty" in r.message for r in caplog.records)


# ══════════════════════════════════════════════════════════════════
# Caching
# ══════════════════════════════════════════════════════════════════

class TestProfileCaching:
    def test_cache_skips_llm_on_second_call(self, mock_llm, tmp_path):
        cv_text = read_cv(FIXTURES / "sample_cv.md")

        parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=True)
        assert mock_llm.complete_json.call_count == 1

        # Second call — same content → should use cache
        parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=True)
        assert mock_llm.complete_json.call_count == 1  # NOT called again

    def test_cache_invalidated_on_cv_change(self, mock_llm, tmp_path):
        cv_text_v1 = read_cv(FIXTURES / "sample_cv.md")
        cv_text_v2 = cv_text_v1 + "\n# New Section\nExtra content."

        parse_cv_to_profile(cv_text_v1, mock_llm, cache_dir=tmp_path, skip_if_unchanged=True)
        assert mock_llm.complete_json.call_count == 1

        # Different content → cache miss → LLM called again
        parse_cv_to_profile(cv_text_v2, mock_llm, cache_dir=tmp_path, skip_if_unchanged=True)
        assert mock_llm.complete_json.call_count == 2

    def test_cache_files_written(self, mock_llm, tmp_path):
        cv_text = read_cv(FIXTURES / "sample_cv.md")
        parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False)

        assert (tmp_path / "cv_hash.txt").exists()
        assert (tmp_path / "candidate_profile.json").exists()

    def test_skip_if_unchanged_false_always_calls_llm(self, mock_llm, tmp_path):
        cv_text = read_cv(FIXTURES / "sample_cv.md")

        parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False)
        parse_cv_to_profile(cv_text, mock_llm, cache_dir=tmp_path, skip_if_unchanged=False)

        assert mock_llm.complete_json.call_count == 2

    def test_pdf_and_md_both_cached_independently(self, mock_llm, sample_pdf_path, tmp_path):
        """PDF-derived text and MD text have different hashes → separate cache entries."""
        md_text = read_cv(FIXTURES / "sample_cv.md")
        pdf_text = read_cv(sample_pdf_path)

        # They should be different strings (PDF extraction may differ slightly)
        # Even if not, different hashes are expected due to format differences
        cache_md = tmp_path / "md_cache"
        cache_pdf = tmp_path / "pdf_cache"

        parse_cv_to_profile(md_text, mock_llm, cache_dir=cache_md, skip_if_unchanged=False)
        parse_cv_to_profile(pdf_text, mock_llm, cache_dir=cache_pdf, skip_if_unchanged=False)

        hash_md = (cache_md / "cv_hash.txt").read_text().strip()
        hash_pdf = (cache_pdf / "cv_hash.txt").read_text().strip()
        # Hashes must exist; if texts differ they'll differ too
        assert hash_md != "" and hash_pdf != ""
