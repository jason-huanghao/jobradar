"""Candidate feedback system — record job preferences to improve future scoring.

Usage:
  jobradar --feedback "AMD liked" "SAP not_interested" "startup preferred"

Writes to memory/feedback.json. The scorer reads this on each run to bias results.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_VALID_ACTIONS = {"liked", "not_interested", "applied", "preferred", "avoided"}


def record_feedback(entries: list[str], cache_dir: Path) -> None:
    """Parse and save feedback entries.

    Each entry is: "<company_or_keyword> <action>"
    Actions: liked, not_interested, applied, preferred, avoided
    """
    feedback_path = cache_dir / "feedback.json"
    existing: list[dict] = []
    if feedback_path.exists():
        try:
            existing = json.loads(feedback_path.read_text())
        except Exception:
            existing = []

    added = 0
    for entry in entries:
        parts = entry.strip().rsplit(" ", 1)
        if len(parts) == 2:
            subject, action = parts
            action = action.lower()
        else:
            subject = entry.strip()
            action = "liked"  # default

        if action not in _VALID_ACTIONS:
            logger.warning("Unknown feedback action '%s' — use: %s", action, ", ".join(_VALID_ACTIONS))
            continue

        existing.append({
            "subject": subject.strip(),
            "action": action,
            "recorded_at": datetime.now().isoformat(),
        })
        added += 1
        print(f"  ✅  Recorded: '{subject}' → {action}")

    cache_dir.mkdir(parents=True, exist_ok=True)
    feedback_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    logger.info("Saved %d feedback entries (%d total)", added, len(existing))


def load_feedback_summary(cache_dir: Path) -> str:
    """Build a feedback summary string for injection into scoring prompts."""
    feedback_path = cache_dir / "feedback.json"
    if not feedback_path.exists():
        return ""

    try:
        entries: list[dict] = json.loads(feedback_path.read_text())
    except Exception:
        return ""

    if not entries:
        return ""

    liked = [e["subject"] for e in entries if e["action"] in ("liked", "preferred")]
    not_interested = [e["subject"] for e in entries if e["action"] in ("not_interested", "avoided")]
    applied = [e["subject"] for e in entries if e["action"] == "applied"]

    lines = ["\n## Candidate Preference Notes (from past feedback)"]
    if liked:
        lines.append(f"- **Positively noted:** {', '.join(liked)}")
    if not_interested:
        lines.append(f"- **Not interested in:** {', '.join(not_interested)}")
    if applied:
        lines.append(f"- **Already applied to:** {', '.join(applied)} (avoid duplicates)")

    return "\n".join(lines)
