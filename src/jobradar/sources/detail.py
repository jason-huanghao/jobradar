"""Shared helpers for enriching a job from its detail page.

Scraper list pages (StepStone, XING) often omit the description; the per-job
detail page exposes it as JSON-LD. These helpers pull that description out and
flatten any embedded HTML to plain text suitable for the LLM scorer.
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup


def strip_html(text: str) -> str:
    """Flatten an HTML (or plain) string to readable plain text."""
    if not text:
        return ""
    if "<" in text and ">" in text:
        return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    return text.strip()


def extract_jsonld_description(html: str) -> str:
    """Return the longest JobPosting description found in the page's JSON-LD,
    flattened to plain text. Returns "" when none is present."""
    soup = BeautifulSoup(html, "html.parser")
    best = ""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                desc = item.get("description") or ""
                if len(desc) > len(best):
                    best = desc
    return strip_html(best)
