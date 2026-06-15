"""Settings & LLM config tests (sub-project #4). No real network/LLM."""
from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from jobradar.config import AppConfig, LLMEndpoint
from jobradar.llm.catalog import ALL, CATALOG, CUSTOM, get_provider
from jobradar.llm.client import LLMClient
from jobradar.llm.connection import test_connection as run_test_connection


def _mem_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


# ── catalog ───────────────────────────────────────────────────────
def test_catalog_lookup():
    assert get_provider("openai").base_url.startswith("https://")
    assert get_provider("nope") is None


def test_catalog_custom_and_local():
    assert CUSTOM.id == "custom"
    assert CUSTOM in ALL and CUSTOM not in CATALOG
    assert get_provider("ollama").local is True


def test_cli_providers_derived_from_catalog():
    from jobradar.interfaces.cli import _PROVIDERS
    labels = {p[0] for p in _PROVIDERS}
    assert {"OpenAI", "Anthropic", "Ollama (local)"} <= labels
    assert len(_PROVIDERS) == len(CATALOG)


# ── test_connection ───────────────────────────────────────────────
_EP = LLMEndpoint(provider="openai", model="m", base_url="http://x/v1", api_key_env="")


def test_connection_ok(monkeypatch):
    monkeypatch.setattr(LLMClient, "complete", lambda self, *a, **k: "OK")
    r = run_test_connection(_EP)
    assert r.ok is True and "OK" in r.message and r.latency_ms >= 0


def test_connection_failure(monkeypatch):
    def boom(self, *a, **k):
        raise RuntimeError("401 unauthorized")
    monkeypatch.setattr(LLMClient, "complete", boom)
    r = run_test_connection(_EP)
    assert r.ok is False and "401" in r.message


# ── UserSettings + repo CRUD ──────────────────────────────────────
def test_user_settings_round_trip():
    from jobradar.storage.models import UserSettings
    eng = _mem_engine()
    with Session(eng) as s:
        s.add(UserSettings(user_email="a@x.com", provider="openai", model="gpt-4o-mini"))
        s.commit()
        row = s.get(UserSettings, "a@x.com")
        assert row.provider == "openai" and row.model == "gpt-4o-mini"


def test_upsert_user_settings_creates_then_updates():
    from jobradar.storage import repo
    eng = _mem_engine()
    with Session(eng) as s:
        assert repo.get_user_settings(s, "a@x.com") is None
        repo.upsert_user_settings(s, "a@x.com", provider="openai", model="m1",
                                  base_url="http://a/v1", api_key_env="OPENAI_API_KEY")
        # user row was created as a side effect
        from jobradar.storage.models import User
        assert s.get(User, "a@x.com") is not None
        repo.upsert_user_settings(s, "a@x.com", provider="anthropic", model="m2")
        row = repo.get_user_settings(s, "a@x.com")
        assert row.provider == "anthropic" and row.model == "m2"
        assert row.base_url == ""   # overwritten by the second upsert


# ── migration 0002 creates the table on a file DB ─────────────────
def test_init_db_creates_user_settings(tmp_path):
    from jobradar.storage.db import get_session, init_db
    from jobradar.storage.models import UserSettings
    db = tmp_path / "jobradar.db"
    init_db(db)
    with next(get_session(db)) as s:
        s.add(UserSettings(user_email="a@x.com", provider="openai"))
        # foreign key to user.email is not enforced by sqlite by default → ok
        s.commit()
        assert s.get(UserSettings, "a@x.com").provider == "openai"


# ── resolve_endpoint ──────────────────────────────────────────────
def test_resolve_endpoint_fallback_to_config():
    from jobradar.llm.resolver import resolve_endpoint
    eng = _mem_engine()
    cfg = AppConfig()
    cfg.llm.text.base_url = "http://config/v1"
    with Session(eng) as s:
        ep = resolve_endpoint(s, "a@x.com", cfg)
    assert ep.base_url == "http://config/v1"


def test_resolve_endpoint_user_override():
    from jobradar.llm.resolver import resolve_endpoint
    from jobradar.storage import repo
    eng = _mem_engine()
    cfg = AppConfig()
    cfg.llm.text.temperature = 0.7
    with Session(eng) as s:
        repo.upsert_user_settings(s, "a@x.com", provider="custom", model="local-llm",
                                  base_url="http://override/v1", api_key_env="MY_KEY")
        ep = resolve_endpoint(s, "a@x.com", cfg)
    assert ep.base_url == "http://override/v1"
    assert ep.model == "local-llm"
    assert ep.api_key_env == "MY_KEY"
    assert ep.temperature == 0.7   # inherited from config


# ── pipeline uses the resolved endpoint ───────────────────────────
def test_pipeline_uses_resolved_endpoint(tmp_path):
    import jobradar.pipeline as pl
    from jobradar.storage import repo
    from jobradar.storage.db import get_session, init_db

    db = tmp_path / "jobradar.db"
    init_db(db)
    with next(get_session(db)) as s:
        repo.upsert_user_settings(s, "a@x.com", provider="custom", model="m",
                                  base_url="http://override/v1", api_key_env="")

    cfg = AppConfig()
    cfg.server.db_path = str(db)
    cfg._config_dir = tmp_path
    pipe = pl.JobRadarPipeline(cfg, user_email="a@x.com")
    assert pipe.llm.endpoint.base_url == "http://override/v1"


# ── API ───────────────────────────────────────────────────────────
def _client(tmp_path):
    from fastapi.testclient import TestClient

    from jobradar.api.main import create_app
    from jobradar.storage.db import init_db
    db = tmp_path / "jobradar.db"
    init_db(db)
    cfg = AppConfig()
    cfg.user.email = "a@x.com"
    cfg.server.db_path = str(db)
    cfg._config_dir = tmp_path
    return TestClient(create_app(cfg))


def test_api_providers(tmp_path):
    resp = _client(tmp_path).get("/api/settings/providers")
    assert resp.status_code == 200
    ids = {p["id"] for p in resp.json()["providers"]}
    assert "custom" in ids and "openai" in ids


def test_api_get_put_settings_and_no_key_leak(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_SECRET_KEY", "super-secret-value")
    client = _client(tmp_path)

    # initially from config (not overridden)
    got = client.get("/api/settings").json()
    assert got["overridden"] is False

    put = client.put("/api/settings", json={
        "provider": "openai", "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1", "api_key_env": "MY_SECRET_KEY",
    })
    assert put.status_code == 200
    body = put.json()
    assert body["overridden"] is True
    assert body["model"] == "gpt-4o-mini"
    assert body["has_key"] is True
    # the secret value must never be returned
    assert "super-secret-value" not in put.text

    again = client.get("/api/settings").json()
    assert again["overridden"] is True and again["api_key_env"] == "MY_SECRET_KEY"


def test_api_test_connection(tmp_path, monkeypatch):
    import jobradar.api.routers.settings as settings_router
    from jobradar.llm.connection import ConnectionResult
    monkeypatch.setattr(settings_router, "test_connection",
                        lambda ep, **k: ConnectionResult(True, "pong", 12))
    resp = _client(tmp_path).post("/api/settings/test", json={
        "provider": "custom", "base_url": "http://x/v1", "model": "m", "api_key_env": "",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True and resp.json()["message"] == "pong"


# ── CLI ───────────────────────────────────────────────────────────
def test_cli_settings(tmp_path):
    from typer.testing import CliRunner

    from jobradar.interfaces.cli import app
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("user:\n  email: a@x.com\nserver:\n  db_path: ./jobradar.db\n")
    result = CliRunner().invoke(app, ["settings", "--config", str(cfg_file)])
    assert result.exit_code == 0, result.output
    assert "a@x.com" in result.output
    assert "Provider" in result.output
