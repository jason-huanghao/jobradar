"""Cleanup-pass regression tests (sub-project #5) — dedup behaviour."""
from __future__ import annotations

from jobradar.config import LLMEndpoint
from jobradar.llm.catalog import CATALOG
from jobradar.llm.client import LLMClient


def _client(provider: str) -> LLMClient:
    return LLMClient(LLMEndpoint(provider=provider, model="m", base_url="http://x/v1"))


def test_complete_auto_skips_json_for_non_json_provider(monkeypatch):
    # volcengine has supports_json_mode=False in the catalog → structured path.
    c = _client("volcengine")
    monkeypatch.setattr(c, "complete_structured", lambda *a, **k: {"via": "structured"})
    monkeypatch.setattr(c, "complete_json", lambda *a, **k: {"via": "json"})
    assert c.complete_auto("hi") == {"via": "structured"}


def test_complete_auto_uses_json_for_json_provider(monkeypatch):
    c = _client("openai")
    monkeypatch.setattr(c, "complete_structured", lambda *a, **k: {"via": "structured"})
    monkeypatch.setattr(c, "complete_json", lambda *a, **k: {"via": "json"})
    assert c.complete_auto("hi") == {"via": "json"}


def test_skill_provider_map_derived_from_catalog():
    from jobradar.interfaces.skill import _PROVIDER_MAP
    for p in CATALOG:
        if p.api_key_env:
            assert _PROVIDER_MAP[p.api_key_env] == (p.base_url, p.default_model)
    # OpenClaw runtime key is the one non-catalog extra.
    assert "OPENCLAW_API_KEY" in _PROVIDER_MAP
