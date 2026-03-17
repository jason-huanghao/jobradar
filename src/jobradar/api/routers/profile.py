"""Profile router — upload CV, get parsed profile."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ...llm.client import LLMClient
from ...profile.ingestor import ingest
from ...storage.db import get_session
from ...storage.models import Candidate
from ..main import get_config

router = APIRouter()


@router.post("/upload")
async def upload_cv(file: UploadFile):
    """Upload a CV file (PDF, DOCX, MD, TXT) and parse it into a profile."""
    cfg = get_config()
    llm = LLMClient(cfg.llm.text)
    cache_dir = cfg.resolve_path(cfg.server.cache_dir)

    suffix = Path(file.filename or "cv").suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        profile = ingest(tmp_path, llm, cache_dir=cache_dir, skip_if_unchanged=False)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return JSONResponse(content=profile.model_dump())


@router.get("")
def get_profile():
    """Return the most recently cached profile."""
    cfg = get_config()
    cache_dir = cfg.resolve_path(cfg.server.cache_dir)
    profile_file = cache_dir / "candidate_profile.json"
    if not profile_file.exists():
        raise HTTPException(status_code=404, detail="No profile found. Upload a CV first.")
    return JSONResponse(content=json.loads(profile_file.read_text()))
