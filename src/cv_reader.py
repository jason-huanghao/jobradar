"""CV file reader — supports .md, .txt, .pdf, .docx, .doc formats.

Usage in cv_parser.py:
    from .cv_reader import read_cv_file
    cv_text = read_cv_file(path)

The returned text is always a plain string suitable for LLM processing.
Format detection is based on file extension (case-insensitive).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_cv_file(cv_path: Path) -> str:
    """Read a CV file and return its text content.

    Supports:
        .md / .txt   — read as UTF-8 text (original behaviour)
        .pdf         — extract text via pypdf
        .docx        — extract text via python-docx
        .doc         — convert via python-docx (limited; full fidelity needs LibreOffice)

    Raises:
        FileNotFoundError  — file does not exist
        ValueError         — unsupported extension
        ImportError        — required library not installed
    """
    cv_path = Path(cv_path)
    if not cv_path.exists():
        raise FileNotFoundError(f"CV not found: {cv_path}")

    suffix = cv_path.suffix.lower()

    if suffix in (".md", ".txt", ""):
        return _read_text(cv_path)
    elif suffix == ".pdf":
        return _read_pdf(cv_path)
    elif suffix in (".docx", ".doc"):
        return _read_docx(cv_path)
    else:
        raise ValueError(
            f"Unsupported CV format: '{suffix}'. "
            "Supported: .md, .txt, .pdf, .docx, .doc"
        )


# ── Format-specific readers ────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Read plain text / Markdown."""
    return path.read_text(encoding="utf-8")


def _read_pdf(path: Path) -> str:
    """Extract text from PDF using pypdf."""
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        raise ImportError(
            "pypdf is required to read PDF CVs.\n"
            "Install it with:  pip install pypdf"
        )

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())

    if not pages:
        logger.warning("PDF '%s' yielded no extractable text (possibly image-only).", path.name)
        return ""

    full_text = "\n\n".join(pages)
    logger.info("PDF '%s': extracted %d chars from %d page(s)", path.name, len(full_text), len(pages))
    return full_text


def _read_docx(path: Path) -> str:
    """Extract text from .docx (and limited .doc) using python-docx."""
    try:
        import docx  # type: ignore  (python-docx)
    except ImportError:
        raise ImportError(
            "python-docx is required to read Word CVs.\n"
            "Install it with:  pip install python-docx"
        )

    if path.suffix.lower() == ".doc":
        logger.warning(
            ".doc format has limited support. Convert to .docx for best results."
        )

    doc = docx.Document(str(path))
    paragraphs: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_texts:
                paragraphs.append(" | ".join(row_texts))

    full_text = "\n".join(paragraphs)
    logger.info("DOCX '%s': extracted %d chars from %d paragraphs",
                path.name, len(full_text), len(paragraphs))
    return full_text


# ── Format detection helper ────────────────────────────────────────


def detect_cv_format(cv_path: Path) -> str:
    """Return a human-readable format label for logging."""
    suffix = Path(cv_path).suffix.lower()
    mapping = {
        ".md": "Markdown",
        ".txt": "Plain text",
        ".pdf": "PDF",
        ".docx": "Word (docx)",
        ".doc": "Word (doc)",
    }
    return mapping.get(suffix, f"Unknown ({suffix})")
