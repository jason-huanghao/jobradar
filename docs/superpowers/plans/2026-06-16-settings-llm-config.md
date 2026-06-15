# Settings & LLM Config — Implementation Plan (sub-project #4)

Spec: `docs/superpowers/specs/2026-06-16-settings-llm-config-design.md`
Tests: `tests/test_settings.py`. Run: `.venv/bin/python -m pytest tests/`. TDD per task.

## Task 1 — `llm/catalog.py`
- Test: `get_provider("openai").base_url` non-empty; `get_provider("nope") is None`;
  `CUSTOM.id == "custom"` and is in the catalog; ollama is `local=True`.
- Impl: `Provider` dataclass + `CATALOG` + `get_provider` + `CUSTOM`.

## Task 2 — refactor `cli.py:_PROVIDERS` to derive from catalog
- Test: the wizard list still contains the expected provider labels (import `_PROVIDERS`,
  assert OpenAI/Anthropic/Ollama present). Keep tuple shape the wizard already expects.
- Impl: build `_PROVIDERS` from `CATALOG`. Surgical — don't touch wizard logic.

## Task 3 — `llm/connection.py`
- Test: monkeypatch `LLMClient.complete` → returns "OK" ⇒ `ok is True`; raises ⇒
  `ok is False` and message contains the error; `latency_ms >= 0`.
- Impl: `ConnectionResult` + `test_connection(endpoint, prompt=...)`.

## Task 4 — `UserSettings` model + migration 0002
- Test: in-memory round-trip of `UserSettings`; fresh `init_db(tmp)` then insert a
  `UserSettings` row (proves migration created the table).
- Impl: `UserSettings` in storage/models.py; import in storage/db.py;
  `migrations/versions/0002_user_settings.py` (down_revision "0001").

## Task 5 — repo CRUD
- Test: `upsert_user_settings` creates then updates (same PK), creates the user row;
  `get_user_settings` returns None when absent.
- Impl: `get_user_settings`, `upsert_user_settings` in storage/repo.py.

## Task 6 — `llm/resolver.py`
- Test: no settings ⇒ returns `config.llm.text`; settings present ⇒ endpoint reflects
  provider/model/base_url/api_key_env, temperature/max_tokens inherited from config.
- Impl: `resolve_endpoint(session, user_email, config)`.

## Task 7 — pipeline uses resolved endpoint
- Test: seed `UserSettings` with a distinctive base_url in a temp DB; construct
  `JobRadarPipeline`; assert `pipe.llm.endpoint.base_url` matches the override.
- Impl: in `__init__`, after `init_db`, open a session and
  `self.llm = LLMClient(resolve_endpoint(session, user_email, config))`.

## Task 8 — API `settings` router
- Test (`TestClient`): `GET /api/settings/providers` lists providers incl. custom;
  `PUT /api/settings` saves and `GET /api/settings` reflects it (overridden True);
  `POST /api/settings/test` returns `ok`/`message` (monkeypatch test_connection);
  responses never include a key value (only `has_key`).
- Impl: `api/routers/settings.py`; mount `/api/settings` in `api/main.py`.

## Task 9 — CLI `jobradar settings`
- Test (`CliRunner`): `jobradar settings --config <tmp>` exit 0, shows provider/model;
  `--test` path monkeypatched.
- Impl: `@app.command("settings")`.

## Task 10 — Full verification
- `.venv/bin/python -m pytest tests/` green; ruff clean on changed files; smoke
  `jobradar settings`; update memory; open PR #4.
