# JobRadar — Project Context for Continuation Sessions

> **Read this first in any new session.** Last updated 2026-06-23.

---

## ⚡ Active work — source data-quality (branch `improve/source-data-quality`, UNCOMMITTED)

Fixing "scored jobs don't match my CV". **Root cause: source data quality, not scoring.**
All sources fetch relevant jobs *by title*, but only `jobspy:indeed` returned
descriptions; `xing`/`stepstone`/`jobspy:linkedin` returned empty descriptions, so the
LLM scored them on title alone → noise. Fixes (95 tests green, ruff clean, verified live
with the Kimi LLM and the test CV):

1. Scorer description budget 400 → 2000 (config `scoring.max_desc_chars`); removed the
   hidden `[:400]` cap in `llm/prompts/job_score.jinja2`.
2. `jobspy_adapter` passes `linkedin_fetch_description=True` for linkedin.
3. `stepstone._parse_article` now extracts the **job** URL (was grabbing the `/cmp/`
   company page → broken links).
4. `xing` uses deterministic `make_id` (was process-salted `hash()`).
5. **Description enrichment**: `sources/detail.py` + `JobSource.fetch_detail()` (xing,
   stepstone) + `SourceRegistry.enrich_descriptions(cap)` + pipeline Step 6a. Config:
   `search.enrich_descriptions=True`, `search.enrich_max=40`. Coverage went indeed-only →
   all 4 sources. Full diagnosis + per-file detail: memory `jobradar-source-quality.md`.

**⚠️ Commit carefully:** the working tree also holds the user's *uncommitted Kimi LLM
work* (`llm/client.py`, `llm/catalog.py`, `llm/env_probe.py`, `profile/extractor.py`, and
a `default_headers` field in `config.py`) that rode along when the branch was created. Do
NOT bundle it into the source-quality commit — stage only the source-quality files +
my `config.py` hunks (enrich_descriptions/enrich_max/max_desc_chars).

---

## TL;DR — where things stand

The **5-sub-project foundation refactor is COMPLETE and MERGED to `main`.**
`main` is at `bd5ecd0` (docs) on top of `41be517`. **95 tests pass on the active branch,
ruff-clean, CI lint gate is blocking.** Remaining work is the active source-quality branch
above plus the deferred items in "Open follow-ups" below.

Verified working on 2026-06-21:
- `pytest tests/` → **83 passed**
- `ruff check src/ tests/` → clean
- `jobradar --help` → all 13 commands load
- `init_db(path)` → 7 tables + `alembic_version`
- `create_app(cfg)` builds; all `/api/...` routes present; skill imports

---

## Identity

| Field | Value |
|-------|-------|
| Package | `openclaw-jobradar` v0.3.6 |
| Local path | `/Users/jason/Documents/projects/jobradar` ⚠️ note: the sibling `jobrader` dir is **empty** (typo) — real repo is `jobradar` |
| GitHub | https://github.com/jason-huanghao/jobradar (remote = `git@github.com:jason-huanghao/jobradar.git`, SSH as `jason-huanghao`) |
| Venv | `.venv/bin/python` (Python 3.11) — created via `uv` (the system python has no pip) |
| Run tests | `cd /Users/jason/Documents/projects/jobradar && .venv/bin/python -m pytest tests/` |
| LLM key | `ARK_API_KEY` in `.env` (Volcengine Ark, doubao) |
| CV | `cv/cv_current.md` |
| DB | SQLite, schema via **Alembic** (`init_db(path)` runs migrations to head). `init_db` takes a **file path, not a SQLAlchemy URL.** |

---

## What shipped — 5 sub-projects, all merged

| # | Squash commit | PR | Tests after | Summary |
|---|---------------|----|-----------|---------|
| 1 | `6e05414` | #1 | 25 | Foundation: User model, clean six-table schema, per-user scoping, Alembic |
| 2 | `bcddad2` | #2 | 41 | Expiry & freshness: deadline/posting-age tracking, `sweep`, read-side hiding |
| 3 | `4bb80ef` | #3 | 65 | Source reliability: health signals, retries, `jobradar sources` |
| 4 | `78a39ea` | #4 | 80 | Settings & LLM config: provider catalog, `UserSettings`, `jobradar settings` |
| 5 | `41be517` | #5 | 83 | Cleanup pass: catalog-driven dedup, zero lint debt, blocking CI lint gate |

Specs + plans live on `main` under `docs/superpowers/specs/` and `docs/superpowers/plans/`.

---

## Architecture (current)

```
src/jobradar/
├── config.py          AppConfig — every field defaults; user.email REQUIRED
│                      (resolve_user_email: --user > config.user.email > error)
├── pipeline.py        JobRadarPipeline(config, user_email).run(mode, on_progress)
│                      Steps: 0 sweep → discover → crawl → filter → score → generate → deliver
│                      (dry-run returns BEFORE the Step 0 sweep)
├── storage/
│   ├── models.py      User · Profile · Job · Score · Application · PipelineRun · UserSettings
│   ├── db.py          get_engine / init_db(path) [Alembic upgrade] / get_session
│   └── repo.py        user/profile resolution, list_scored(include_expired=False),
│                      scored_job_ids, sweep_expired, recent_source_health,
│                      get/upsert_user_settings, get_active_profile
├── scoring/
│   ├── freshness.py   SINGLE source of truth for expiry date math
│   ├── hard_filter.py free pre-filter
│   ├── scorer.py      6-dim LLM scoring (batched); json-mode via catalog.supports_json_mode
│   └── generator/     cover_letter.py + cv_optimizer.py
├── sources/
│   ├── registry.py    parallel fetch + retry (reliability.*); registry.last_outcomes
│   ├── health.py      SourceOutcome + classify → ok·empty·error·blocked; SourceError(blocked=)
│   ├── report.py      source × recent-health join (for CLI + API)
│   └── adapters/      arbeitsagentur, jobspy(indeed+google+glassdoor), stepstone, xing,
│                      bosszhipin, lagou, zhilian  (JobSource.kind = api/library/scraper)
├── llm/
│   ├── catalog.py     curated Provider catalog — SINGLE source of truth.
│   │                  cli._PROVIDERS and skill._PROVIDER_MAP both derive from this.
│   ├── resolver.py    resolve_endpoint(session, user_email, cfg): per-user override > config
│   ├── connection.py  test_connection(endpoint) → ConnectionResult
│   ├── client.py      OpenAI-compatible LLMClient
│   └── env_probe.py   detect endpoint from env / Claude OAuth / OpenClaw
│                      (NOTE: env_probe._PROBE_TABLE still overlaps catalog — left intentionally,
│                       different concern; not dead code)
├── apply/             engine.run_apply(db_path, profile_id, confirm=callback, on_result=…)
│                      base · boss(直聘 greet) · linkedin(Easy Apply) · history
├── report/            generator.load_report_jobs(db_path, profile_id, min_score) + HTML;
│                      publisher → GitHub Pages
├── api/               FastAPI. create_app(cfg) (config is a module global in api/main.py).
│                      routers: jobs, generate, outputs, profile, pipeline, settings, sources
│                      deps.py: get_db_path / get_user_email (per-user DI). ws.py: pipeline progress.
│                      All routes under /api/...
└── interfaces/
    ├── cli.py         Typer. Commands below. `run` is an alias of `update`.
    └── skill.py       OpenClaw skill entry point

migrations/versions/   0001_initial.py · 0002_user_settings.py
```

### Schema (six core tables + user_settings)
`user` (identity by email) → versioned `profile` (the CV) → `score` keyed on
`(profile_id, job_id)` and `application`. `job` is global. `pipeline_run` is scoped.
`user_settings` keyed by user email stores LLM endpoint **selection only — never the
secret** (just the `api_key_env` name). `init_db` → these 7 + `alembic_version`.

---

## CLI Reference (current)

`run` == `update`. Every per-user command accepts `--user EMAIL` (falls back to
`config.user.email`).

```bash
jobradar init [--cv … --email … --api-key ENV=val --locations "…" -y]
jobradar setup                 # non-interactive config.yaml copy
jobradar health | status
jobradar update [--mode full|quick|score-only|dry-run] [--cv …] [--limit N] [--user …]
jobradar sweep                 # flag stale/expired (global)
jobradar sources               # per-source kind + reliability health
jobradar settings [--test]     # effective LLM endpoint; --test pings it
jobradar report [--publish --min-score N --no-open --user …]
jobradar apply [--dry-run --auto --min-score N --platforms … --user …]
jobradar web [--port N --no-browser]
jobradar install-agent         # macOS launchd: daily `update --mode quick` 08:00
```

---

## Key invariants & gotchas (don't relearn these the hard way)

- **`init_db(path)` takes a filesystem path, not a URL.** It runs Alembic to head.
- **Identity is required.** Fetch/score/report/apply resolve a user via
  `resolve_user_email` (raises a clear ValueError if none). Single-user installs set
  `user.email` once in `config.yaml` / `jobradar init --email`.
- **Expiry is flag-only, never delete.** A job is expired if ANY of: past `valid_through`,
  `date_posted + max_days_old`, or `last_seen_at + staleness_days`. `list_scored`
  hides expired by default — that's the choke point for API/report/apply.
- **LLM provider catalog is the single source of truth** (`llm/catalog.py`). If you add
  a provider, add it there; CLI + skill derive from it. `supports_json_mode` drives
  scorer json-mode (no hardcoded blocklists).
- **CI lint is BLOCKING** (`ruff check src/ tests/`, no `|| true`). E501 globally ignored
  in pyproject. **ruff is pinned `0.15.*`** in dev deps so the gate is reproducible —
  don't bump it casually.
- **dry-run pipeline returns before Step 0 sweep** and before any network call.
- The empty sibling dir `…/jobrader` is a typo; always work in `…/jobradar`.

---

## Open follow-ups (next candidate work)

1. **#3b — Hardened Playwright browser crawler** (deferred from sub-project #3,
   instrument-first rationale: browser binaries too heavy for pip+pytest CI until the
   new per-source health data shows which scraper actually needs it). Tracked as a
   spawned-task chip.
2. **Live integration tests** never run in this environment (no live keys/cookies/network):
   - `jobradar update` against real sources end-to-end
   - `jobradar report --publish` to GitHub Pages (needs Pages enabled on the repo)
   - BOSS直聘 / LinkedIn live apply (need `BOSSZHIPIN_COOKIES` / `LINKEDIN_COOKIES`)
   - OpenClaw skill live conversation
3. Roadmap items in README (51job source, Telegram/email digest, MCP server mode,
   Docker one-liner, OpenClaw Cron).

---

## Working agreement (from the user, 2026-06-16, still in force)

> "Continue until the whole project [is] done. Do the work as a professional product
> manager, do not ask my opinion from now on!"

→ Act autonomously: make design calls yourself and document them; don't use
AskUserQuestion for design opinions. Open PRs for the user to review/merge async.
The superpowers workflow (brainstorm spec → write plan → execute with TDD → request
review → finish branch) was used for every sub-project and should continue.
```
