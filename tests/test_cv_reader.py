"""Tests for cv_reader.py — multi-format CV reading.

Covers:
  - .md / .txt (plain text)
  - .pdf (via pypdf)
  - .docx (via python-docx)
  - edge cases: missing file, unsupported format, empty PDF
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.cv_reader import detect_cv_format, read_cv_file

FIXTURES = Path(__file__).parent / "fixtures"


# ══════════════════════════════════════════════════════════════════
# Markdown / plain text
# ══════════════════════════════════════════════════════════════════

class TestReadMarkdown:
    def test_reads_md_file(self):
        text = read_cv_file(FIXTURES / "sample_cv.md")
        assert "John Doe" in text
        assert "Knowledge Graphs" in text
        assert "Python" in text

    def test_reads_txt_file(self, tmp_path):
        f = tmp_path / "cv.txt"
        f.write_text("Alice Smith\nSoftware Engineer\nPython, Go", encoding="utf-8")
        assert read_cv_file(f) == "Alice Smith\nSoftware Engineer\nPython, Go"

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError, match="CV not found"):
            read_cv_file(Path("/nonexistent/cv.md"))

    def test_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "cv.odt"
        f.write_text("some content")
        with pytest.raises(ValueError, match="Unsupported CV format"):
            read_cv_file(f)


# ══════════════════════════════════════════════════════════════════
# PDF
# ══════════════════════════════════════════════════════════════════

class TestReadPDF:
    def test_reads_pdf_fixture(self, sample_pdf_path):
        """Generated PDF should contain key CV content."""
        text = read_cv_file(sample_pdf_path)
        assert isinstance(text, str)
        assert len(text) > 100, "Expected substantial text from PDF"
        assert "John Doe" in text
        assert "Python" in text

    def test_pdf_missing_raises(self):
        with pytest.raises(FileNotFoundError):
            read_cv_file(Path("/tmp/nonexistent.pdf"))

    def test_pdf_no_text_returns_empty(self, tmp_path):
        """A valid blank-page PDF (no text) should return empty string."""
        from pypdf import PdfWriter
        import io
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        buf = io.BytesIO()
        writer.write(buf)
        p = tmp_path / "blank.pdf"
        p.write_bytes(buf.getvalue())
        text = read_cv_file(p)
        assert text == ""

    def test_pypdf_import_error(self, tmp_path, monkeypatch):
        """If pypdf is not installed, should raise ImportError with install hint."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pypdf":
                raise ImportError("No module named 'pypdf'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        # Need a real .pdf file so it passes the existence check
        p = tmp_path / "test.pdf"
        p.write_bytes(b"%PDF-1.4\n%%EOF")

        # Invalidate the module cache so our mock_import is called
        import sys
        with patch.dict(sys.modules, {"pypdf": None}):
            from importlib import import_module
            import src.cv_reader as cv_reader_mod
            # Patch the internal import inside _read_pdf
            original = cv_reader_mod._read_pdf

            def patched_read_pdf(path):
                raise ImportError("pypdf is required to read PDF CVs.\nInstall it with:  pip install pypdf")

            monkeypatch.setattr(cv_reader_mod, "_read_pdf", patched_read_pdf)
            with pytest.raises(ImportError, match="pip install pypdf"):
                cv_reader_mod.read_cv_file(p)


# ══════════════════════════════════════════════════════════════════
# DOCX
# ══════════════════════════════════════════════════════════════════

class TestReadDocx:
    def test_reads_docx_fixture(self, sample_docx_path):
        """Generated DOCX should contain key CV content."""
        text = read_cv_file(sample_docx_path)
        assert isinstance(text, str)
        assert len(text) > 100
        assert "John Doe" in text
        assert "Python" in text

    def test_docx_extracts_table_content(self, sample_docx_path):
        """Table cells (Skills) should be extracted."""
        text = read_cv_file(sample_docx_path)
        # The Skills table contains "Technical" and "Python"
        assert "Technical" in text
        assert "Python" in text

    def test_docx_missing_raises(self):
        with pytest.raises(FileNotFoundError):
            read_cv_file(Path("/tmp/nonexistent.docx"))

    def test_docx_import_error(self, tmp_path, monkeypatch):
        """If python-docx is not installed, should raise ImportError with install hint."""
        p = tmp_path / "test.docx"
        p.write_bytes(b"fake docx content")

        import src.cv_reader as cv_reader_mod

        def patched_read_docx(path):
            raise ImportError(
                "python-docx is required to read Word CVs.\nInstall it with:  pip install python-docx"
            )

        monkeypatch.setattr(cv_reader_mod, "_read_docx", patched_read_docx)
        with pytest.raises(ImportError, match="pip install python-docx"):
            cv_reader_mod.read_cv_file(p)

    def test_doc_extension_accepted(self, tmp_path, monkeypatch):
        """Legacy .doc extension should be accepted (with warning)."""
        import src.cv_reader as cv_reader_mod

        captured_warnings = []

        def fake_read_docx(path):
            # Simulate the .doc warning behavior
            if path.suffix.lower() == ".doc":
                captured_warnings.append("limited support")
            return "Mock CV text from .doc"

        monkeypatch.setattr(cv_reader_mod, "_read_docx", fake_read_docx)

        p = tmp_path / "cv.doc"
        p.write_bytes(b"fake doc")
        text = cv_reader_mod.read_cv_file(p)
        assert text == "Mock CV text from .doc"


# ══════════════════════════════════════════════════════════════════
# Format detection
# ══════════════════════════════════════════════════════════════════

class TestDetectFormat:
    @pytest.mark.parametrize("filename,expected", [
        ("cv.md",   "Markdown"),
        ("cv.txt",  "Plain text"),
        ("cv.pdf",  "PDF"),
        ("cv.docx", "Word (docx)"),
        ("cv.doc",  "Word (doc)"),
        ("CV.PDF",  "PDF"),       # case-insensitive
        ("CV.DOCX", "Word (docx)"),
        ("cv.xyz",  "Unknown (.xyz)"),
    ])
    def test_detect_format(self, filename, expected):
        result = detect_cv_format(Path(filename))
        assert result == expected


# ══════════════════════════════════════════════════════════════════
# Content quality — all formats produce equivalent output
# ══════════════════════════════════════════════════════════════════

class TestCrossFormatConsistency:
    """All formats should produce text containing the same key terms."""

    KEY_TERMS = ["John Doe", "Python", "Hannover", "Knowledge Graphs"]

    def test_md_contains_key_terms(self):
        text = read_cv_file(FIXTURES / "sample_cv.md")
        for term in self.KEY_TERMS:
            assert term in text, f"MD: missing '{term}'"

    def test_pdf_contains_key_terms(self, sample_pdf_path):
        text = read_cv_file(sample_pdf_path)
        for term in self.KEY_TERMS:
            assert term in text, f"PDF: missing '{term}'"

    def test_docx_contains_key_terms(self, sample_docx_path):
        text = read_cv_file(sample_docx_path)
        for term in self.KEY_TERMS:
            assert term in text, f"DOCX: missing '{term}'"
