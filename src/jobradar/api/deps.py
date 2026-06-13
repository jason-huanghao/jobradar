"""FastAPI dependencies — DB path resolution and user-email resolution."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Query

from ..config import resolve_user_email
from .main import get_config


def get_db_path() -> Path:
    cfg = get_config()
    return cfg.resolve_path(cfg.server.db_path)


def get_user_email(user_email: str = Query(default="")) -> str:
    try:
        return resolve_user_email(get_config(), user_email or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
