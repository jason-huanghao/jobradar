"""Application history — prevents re-applying and enforces daily limits."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path


class ApplyHistory:
    """Persistent JSON store tracking applied jobs and daily counts.

    File location: ~/.jobradar/apply_history.json
    Structure:
        {
          "applied": {"job_id": "2026-03-17T10:00:00", ...},
          "daily":   {"2026-03-17": 12, ...}
        }
    """

    def __init__(self, path: Path | None = None):
        self._path = path or (Path.home() / ".jobradar" / "apply_history.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def already_applied(self, job_id: str) -> bool:
        return job_id in self._data["applied"]

    def record(self, job_id: str) -> None:
        today = str(date.today())
        self._data["applied"][job_id] = datetime.utcnow().isoformat()
        self._data["daily"][today] = self._data["daily"].get(today, 0) + 1
        self._save()

    def daily_count(self) -> int:
        return self._data["daily"].get(str(date.today()), 0)

    def total_applied(self) -> int:
        return len(self._data["applied"])

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                pass
        return {"applied": {}, "daily": {}}

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
