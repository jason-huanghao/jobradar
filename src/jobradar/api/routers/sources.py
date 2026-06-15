"""Sources router — per-source reliability health for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...sources.report import source_report
from ...storage.db import get_session
from ..deps import get_db_path
from ..main import get_config

router = APIRouter()


@router.get("")
def list_sources(db_path=Depends(get_db_path)):
    cfg = get_config()
    with next(get_session(db_path)) as session:
        rows = source_report(session, cfg)
    return {"sources": rows}
