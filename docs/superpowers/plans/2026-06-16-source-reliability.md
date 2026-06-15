# Source Reliability — Implementation Plan (sub-project #3)

Spec: `docs/superpowers/specs/2026-06-16-source-reliability-design.md`
Approach: TDD. Tests in `tests/test_source_reliability.py` unless noted.
Run: `.venv/bin/python -m pytest tests/`

Each task: write the test (red) → implement (green) → keep all prior tests green.

## Task 1 — `SourceOutcome` + `classify` (sources/health.py)
- Test: `classify(5, None) == "ok"`, `classify(0, None) == "empty"`,
  `classify(0, ValueError()) == "error"`, `classify(0, SourceError("x", blocked=True))
  == "blocked"`, `classify(3, SourceError(...)) == "error"` (error wins over jobs).
- Test: `SourceOutcome` `to_dict`/`from_dict` round-trip; error message truncated to 200.
- Test: `status_is_failure("blocked") is True`, `status_is_failure("empty") is False`.
- Impl: `sources/health.py`. `SourceError` lives in `base.py` (Task 2) — import it.
- Verify: `pytest tests/test_source_reliability.py -k classify`.

## Task 2 — `SourceError` + `kind` on base (sources/base.py)
- Test: `SourceError("blocked", blocked=True).blocked is True`; default `blocked is
  False`; `JobSource.kind == "scraper"`.
- Impl: add `SourceError` class + `kind: str = "scraper"` class attr to `JobSource`.
- Note: `health.py` imports `SourceError` from `base` — do Task 2 before/with Task 1.
- Verify: `pytest -k "source_error or kind"`.

## Task 3 — `ReliabilityConfig` (config.py)
- Test: `AppConfig().reliability.max_attempts == 2` and `retry_base_delay == 0.5`;
  loading a config.yaml with `reliability: {max_attempts: 3}` overrides.
- Impl: `ReliabilityConfig(BaseModel)` + `AppConfig.reliability` field.
- Verify: `pytest -k reliability_config`.

## Task 4 — Registry instrumentation + retry (sources/registry.py)
- Test (use a fake in-registry source): source that raises `SourceError` twice then
  succeeds → with `max_attempts=3`, `last_outcomes` has one `ok` with `attempts == 3`.
- Test: source raising `SourceError` every time, `max_attempts=2` → outcome `error`/
  `blocked`, `attempts == 2`, jobs from that source absent.
- Test: source raising a plain `ValueError` → outcome `error`, `attempts == 1` (no retry).
- Test: source returning `[]` → outcome `empty`; source returning jobs → `ok`.
- Test: `fetch_all` still returns `list[RawJob]` (other sources continue when one fails).
- Impl: add `self.last_outcomes` (init `[]`), `_run` returns `(outcome, jobs)`; retry
  wrapper honoring `config.reliability`; `time.monotonic()` timing; classify outcome.
  Preserve `on_source_done(sid, count)`.
- Verify: `pytest -k registry`.

## Task 5 — Adapter `kind` + StepStone/XING raise SourceError
- Test: `ArbeitsagenturSource.kind == "api"`, `JobSpySource.kind == "library"`,
  `StepstoneSource.kind == "scraper"`.
- Test: monkeypatch `httpx.Client.get` to return a 403 → `StepstoneSource().fetch([q],
  since)` raises `SourceError` with `blocked is True`; 500 → `blocked is False`.
  (Same for XING.)
- Impl: set `kind` on the three adapters; in stepstone/xing `_search`, replace the
  non-200 `return []` with `raise SourceError(..., blocked=status in (403, 429))` and the
  outer network `except: return []` with `raise SourceError(str(e))`. Keep per-query
  continue semantics in `fetch` (a single raising query fails the source — acceptable;
  these adapters issue one request path per query and already aggregate).
- Verify: `pytest -k "kind or blocked"`.

## Task 6 — Persist outcomes (pipeline.py)
- Test: run pipeline in a mode that fetches, with registry monkeypatched to set
  `last_outcomes`; assert the persisted `PipelineRun.sources_run` JSON parses to the
  outcomes. (Reuse the foundation test harness pattern: monkeypatch `fetch_all` to set
  `last_outcomes` and return jobs.)
- Impl: in `run()`, after `_execute`, set `run_record.sources_run =
  json.dumps([o.to_dict() for o in self._registry.last_outcomes])` before final commit.
  Guard for the monkeypatched/empty case (`getattr(self._registry, "last_outcomes", [])`).
- Verify: `pytest -k persist_sources_run` + full suite.

## Task 7 — `recent_source_health` (storage/repo.py)
- Test: seed 3 `PipelineRun` rows with crafted `sources_run`; assert per-source
  `last_status`, `last_jobs`, `consecutive_failures` (newest-first until first
  non-failure), `last_ok_at` set to the newest ok run, and sources only in older runs
  still appear.
- Impl: `recent_source_health(session, limit=20)` reading newest-first pipeline_run rows.
- Verify: `pytest -k recent_source_health`.

## Task 8 — CLI `jobradar sources`
- Test: invoke via Typer's `CliRunner` against a temp DB/config → exit 0, lists each
  registered source with its kind; tolerates empty health.
- Impl: `@app.command("sources")` — load config, build registry, init_db, call
  `recent_source_health`, render Rich table.
- Verify: `pytest -k cli_sources`.

## Task 9 — API `GET /api/sources`
- Test: `TestClient(create_app(cfg))` GET `/api/sources` → 200, `sources` list with
  expected keys; works with empty DB.
- Impl: `api/routers/sources.py` (router), mount in `api/main.py` at `/api/sources`.
- Verify: `pytest -k api_sources`.

## Task 10 — Full verification
- `.venv/bin/python -m pytest tests/` all green.
- `.venv/bin/ruff check` on changed files clean.
- Smoke: `jobradar sources` against a fresh temp project dir.
- Update memory; open PR #3.
