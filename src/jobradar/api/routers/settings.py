"""Settings router — per-user LLM endpoint: catalog, view, save, test.

Never returns secret key values — only ``has_key`` (whether the env var is set).
"""

from __future__ import annotations

import os
from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...config import LLMEndpoint
from ...llm.catalog import ALL
from ...llm.connection import test_connection
from ...llm.resolver import resolve_endpoint
from ...storage.db import get_session
from ...storage.repo import get_user_settings, upsert_user_settings
from ..deps import get_db_path, get_user_email
from ..main import get_config

router = APIRouter()


class SettingsBody(BaseModel):
    provider: str = ""
    model: str = ""
    base_url: str = ""
    api_key_env: str = ""


def _summary(endpoint: LLMEndpoint, overridden: bool) -> dict:
    return {
        "provider": endpoint.provider,
        "model": endpoint.model,
        "base_url": endpoint.base_url,
        "api_key_env": endpoint.api_key_env,
        "has_key": bool(endpoint.api_key_env and os.getenv(endpoint.api_key_env)),
        "overridden": overridden,
    }


@router.get("/providers")
def list_providers():
    return {"providers": [asdict(p) for p in ALL]}


@router.get("")
def get_settings(db_path=Depends(get_db_path), user_email: str = Depends(get_user_email)):
    cfg = get_config()
    with next(get_session(db_path)) as session:
        overridden = get_user_settings(session, user_email) is not None
        endpoint = resolve_endpoint(session, user_email, cfg)
    return _summary(endpoint, overridden)


@router.put("")
def save_settings(
    body: SettingsBody,
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    cfg = get_config()
    with next(get_session(db_path)) as session:
        upsert_user_settings(
            session, user_email,
            provider=body.provider, model=body.model,
            base_url=body.base_url, api_key_env=body.api_key_env,
        )
        endpoint = resolve_endpoint(session, user_email, cfg)
        return _summary(endpoint, overridden=True)


@router.post("/test")
def test_settings(
    body: SettingsBody | None = None,
    db_path=Depends(get_db_path),
    user_email: str = Depends(get_user_email),
):
    cfg = get_config()
    if body and (body.provider or body.base_url):
        endpoint = LLMEndpoint(
            provider=body.provider, model=body.model,
            base_url=body.base_url, api_key_env=body.api_key_env,
            temperature=cfg.llm.text.temperature, max_tokens=cfg.llm.text.max_tokens,
        )
    else:
        with next(get_session(db_path)) as session:
            endpoint = resolve_endpoint(session, user_email, cfg)
    result = test_connection(endpoint)
    return {"ok": result.ok, "message": result.message, "latency_ms": result.latency_ms}
