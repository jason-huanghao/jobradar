"""Assemble the per-source reliability report shared by the CLI and API.

Joins the static registry (which sources exist, their kind, whether enabled)
with the rolling health derived from recent pipeline runs.
"""

from __future__ import annotations

from sqlmodel import Session

from ..config import AppConfig
from ..storage.repo import recent_source_health
from .registry import build_registry


def source_report(session: Session, config: AppConfig) -> list[dict]:
    """One dict per registered source: identity + config + rolling health."""
    registry = build_registry(config)
    health = recent_source_health(session)
    rows: list[dict] = []
    for sid, src in sorted(registry.sources.items()):
        h = health.get(sid, {})
        last_ok = h.get("last_ok_at")
        rows.append({
            "source_id": sid,
            "kind": src.kind,
            "enabled": src.is_enabled(config),
            "last_status": h.get("last_status"),
            "last_jobs": h.get("last_jobs"),
            "consecutive_failures": h.get("consecutive_failures", 0),
            "last_ok_at": last_ok.isoformat() if last_ok else None,
        })
    return rows
