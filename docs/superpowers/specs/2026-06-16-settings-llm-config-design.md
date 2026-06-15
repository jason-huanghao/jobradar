# Settings & LLM Config Layer — Design Spec (sub-project #4)

**Status:** approved (PM-authored, autonomous)
**Date:** 2026-06-16
**Branch:** `refactor/settings-llm-config`
**Depends on:** #1, #2, #3 — all merged to `main`.

## Problem

LLM configuration today is global and scattered:

- The provider list is **duplicated**: `interfaces/cli.py:_PROVIDERS` (wizard) and
  `llm/env_probe.py:_PROBE_TABLE` (auto-detect) each hardcode provider name / base_url /
  default model independently.
- There is **no per-user config**, yet the locked architecture says identity =
  `user.email` and *settings/LLM config live on the user* (`User` model docstring even
  says "Holds settings/LLM config in later sub-projects"). Every path uses the single
  global `config.llm.text`.
- There is **no first-class "test connection"** primitive; `jobradar health` open-codes a
  ping, and the web UI has no way to validate a key before running.
- No **custom OpenAI-compatible** escape hatch surfaced as a real option (the
  `LLMEndpoint` supports arbitrary base_url, but nothing exposes "bring your own
  endpoint" as a catalog choice).

## Scope (PM)

Deliver the per-user settings + LLM config layer:

1. **Curated provider catalog** — one source of truth (`llm/catalog.py`).
2. **Custom OpenAI-compatible fallback** — a `custom` catalog entry.
3. **Test-connection** primitive — `llm/connection.py`, reused by CLI + API + wizard.
4. **Per-user settings storage** — `UserSettings` table (migration `0002`), keyed by
   `user.email`; stores the *endpoint selection* (provider/model/base_url/api_key_env),
   **never the secret key** (keys stay in env/.env, matching today's security model).
5. **Resolution** — `resolve_endpoint(session, user_email, config)`: per-user DB settings
   override `config.llm.text`; pipeline uses the resolved endpoint.
6. **Surfacing** — `jobradar settings` CLI + `/api/settings*` routes.

### Security note
We persist only the **env-var name** that holds the key (`api_key_env`), not the key
value. This keeps secrets out of the DB and is consistent with `LLMEndpoint.api_key`
reading `os.getenv(api_key_env)`. The API never returns key values — only `has_key: bool`.

## Design

### 1. `llm/catalog.py` — curated provider catalog

```python
@dataclass(frozen=True)
class Provider:
    id: str                 # "openai", "anthropic", "volcengine", "ollama", "custom", …
    label: str
    base_url: str
    default_model: str
    api_key_env: str        # "" for local (ollama/lm_studio) and custom
    local: bool = False     # no key required
    supports_json_mode: bool = True

CATALOG: list[Provider]          # curated list
def get_provider(id: str) -> Provider | None
CUSTOM = Provider("custom", "Custom (OpenAI-compatible)", "", "", "", supports_json_mode=True)
```

`interfaces/cli.py:_PROVIDERS` is refactored to derive from `CATALOG` (kills the wizard
duplication). `env_probe._PROBE_TABLE` stays (its concern is env-var *scan order* for
auto-detect, not catalog presentation) — overlap noted for cleanup #5.

### 2. `llm/connection.py` — test connection

```python
@dataclass
class ConnectionResult:
    ok: bool
    message: str
    latency_ms: int = 0

def test_connection(endpoint: LLMEndpoint, *, prompt: str = "Say OK.") -> ConnectionResult
```

Builds an `LLMClient`, issues one tiny `complete()`, times it, maps exceptions to a
friendly message. Pure given an endpoint — tests monkeypatch `LLMClient.complete`.

### 3. `UserSettings` table (storage/models.py + migration 0002)

```python
class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"
    user_email: str = Field(primary_key=True, foreign_key="user.email")
    provider: str = ""          # catalog id, or "custom"
    model: str = ""
    base_url: str = ""
    api_key_env: str = ""
    updated_at: datetime = Field(default_factory=_utcnow)
```

Migration `migrations/versions/0002_user_settings.py` (down_revision `0001`) creates the
table. In-memory tests get it free via `SQLModel.metadata.create_all`.

### 4. repo CRUD (storage/repo.py)

```python
def get_user_settings(session, user_email) -> UserSettings | None
def upsert_user_settings(session, user_email, *, provider, model, base_url, api_key_env)
    -> UserSettings           # creates the user row if missing (resolve_or_create_user)
```

### 5. `llm/resolver.py` — effective endpoint

```python
def resolve_endpoint(session, user_email, config) -> LLMEndpoint:
    s = get_user_settings(session, user_email)
    if s is None or not (s.provider or s.base_url):
        return config.llm.text
    # Build from settings; inherit temperature/max_tokens/rate_limit from config.llm.text
    return LLMEndpoint(provider=s.provider, model=s.model, base_url=s.base_url,
                       api_key_env=s.api_key_env, temperature=…, max_tokens=…)
```

Pipeline wiring: `JobRadarPipeline.__init__` opens a session after `init_db` and sets
`self.llm = LLMClient(resolve_endpoint(session, user_email, config))`. Falls back to
`config.llm.text` when the user has no settings (current behaviour preserved).

### 6. API `api/routers/settings.py` (mounted `/api/settings`)

- `GET  /api/settings/providers` → `{"providers": [catalog as dicts incl. custom]}`
- `GET  /api/settings` (user_email dep) → effective endpoint summary
  `{provider, model, base_url, api_key_env, has_key, overridden}`
- `PUT  /api/settings` (user_email dep, body: provider/model/base_url/api_key_env) →
  upsert, returns the new effective summary
- `POST /api/settings/test` (body: optional endpoint override, else effective) →
  `ConnectionResult` as JSON

Never returns key values; `has_key = bool(os.getenv(api_key_env))`.

### 7. CLI `jobradar settings`

```
jobradar settings [--user EMAIL] [--test]
```
Shows: effective provider/model/base_url, whether it is a per-user override or from
config, and whether the key env var is set. `--test` runs `test_connection` and prints
the result. (Saving stays in the `init` wizard + API; out of scope to add a CLI setter.)

## Out of scope (this PR)

- Migrating `env_probe._PROBE_TABLE` onto the catalog (cleanup #5).
- Storing non-LLM settings (search prefs, etc.) on `UserSettings` — add columns later when
  a feature needs them; YAGNI now.
- A CLI `settings set` subcommand (wizard + API cover writes).
- Updating `api/routers/profile.py` upload path to per-user endpoints (low value; uses
  global config for the one-off parse).

## Success criteria

1. `tests/test_settings.py` covers: catalog lookup + custom entry; `test_connection`
   ok/failure (mocked client); `UserSettings` round-trip; `get/upsert_user_settings`;
   `resolve_endpoint` (override vs fallback); pipeline uses resolved endpoint;
   `/api/settings/providers`, `GET/PUT /api/settings`, `POST /api/settings/test` shapes;
   key values never leaked (only `has_key`).
2. Fresh `init_db` creates `user_settings` (migration 0002 runs); all pre-existing tests
   still pass.
3. `jobradar settings` runs against a fresh DB.
4. New/edited files ruff-clean (pre-existing debt untouched).
