# JobRadar Refactor — Sub-project #1: Foundation (User Model + Clean Schema + Per-User Scoping)

> Status: Design approved 2026-06-13. First of five sub-projects in the JobRadar refactor.

## Context

JobRadar is an AI job-search agent (scrape → score → apply) currently architected
around a single hidden assumption: one user, one machine, one CV. A review identified
that this assumption leaks into the data model and read paths, causing five user-reported
problems. The largest and most foundational is multi-user scoping: scores are stored
per-candidate but every read path ignores `candidate_id`, so listings, reports, and
auto-apply blend or arbitrarily pick candidates.

This sub-project rebuilds the data foundation so the remaining work (expiry filtering,
source reliability, settings/LLM config, cleanup) can layer on cleanly.

### Decisions locked during brainstorming

- **Product shape:** Multi-tenant backend, same frontends. CLI + skill stay primary;
  only a light settings UI later. Multiple people can share one deployment.
- **Identity:** User = email (stable, holds settings + LLM config). Each CV is a
  versioned `profile` under the user. Scores key on `(profile_id, job_id)`.
- **Schema strategy:** Clean redesign from scratch. **Discard the existing ~800-job DB**
  (most rows are expired). No importer/backfill. Set up Alembic for forward evolution.
- **Source strategy (later sub-project #3):** Hybrid — API-first where APIs exist,
  one hardened Playwright crawler for no-API sources, per-source health signals.
- **LLM config (later sub-project #4):** Curated provider catalog + custom
  OpenAI-compatible fallback + test-connection, scoped per user.

### Overall decomposition (this spec covers #1 only)

| # | Sub-project | Covers |
|---|---|---|
| **1** | **Foundation: User model + clean schema + per-user scoping + migrations** (this spec) | per-person separation |
| 2 | Expiry & freshness (read-side recency/expiry filtering + sweep) | stale/expired jobs |
| 3 | Source reliability (hybrid adapters + source health) | broken platforms |
| 4 | Settings & LLM config layer (catalog/custom + test-connection) | settings UI / multi-provider |
| 5 | Cleanup pass (CLI/skill dedup, truncation, complete_auto blocklist, etc.) | code cleanliness |

Cleanup is handled opportunistically inside sub-projects 1–4 (fix what we touch) plus a
final dedicated pass (#5).

## Goals

- A clean six-table schema where user-scoping is structural, not bolted on.
- Identity (`user.email`) resolved explicitly and threaded through pipeline + all read paths.
- The blended/arbitrary-candidate read bug fixed in `jobs.py`, `report/`, and `apply/`.
- Alembic migrations so subsequent sub-projects can evolve the schema safely.
- Expiry columns placed now (filtering logic deferred to #2) to avoid re-migrating.
- A scoping-focused, LLM-mocked test suite that becomes the regression net.

## Non-goals (YAGNI)

- No auth/passwords/login. Multi-tenant by key, not by session.
- No per-CV-version score-comparison UI (the `profile_id` key keeps it *possible* later).
- No replacement of the LLM env-probe yet (sub-project #4).
- No new/hardened source adapters yet (sub-project #3), beyond the deterministic-ID fix.
- No data import from the old DB.

## Schema (six tables)

**`user`** — stable identity
- `email` (PK), `display_name`, `created_at`
- Settings live in their own tables (sub-project #4), not here.

**`profile`** — a versioned CV under a user
- `id` (PK, uuid), `user_email` (FK→user.email), `version` (int, per-user incrementing),
  `cv_source` (path/URL), `profile_json` (serialized CandidateProfile), `is_active` (bool),
  `created_at`
- Exactly one `is_active` profile per user. Re-uploading a CV creates a new version and
  flips the active flag.

**`job`** — global, objective listing (shared across users)
- `id` (PK = `sha256(source + canonical_url)`), `source`, `title`, `company`, `location`,
  `description`, `url`, `salary`, `remote`, `job_type`, `raw_extra` (JSON)
- `date_posted`, `valid_through` (deadline, nullable; parsed from JSON-LD when available),
  `expires_at` (computed: `valid_through` or `date_posted + max_days_old`),
  `status` (`active` | `expired`)
- `fetched_at`, `last_seen_at`
- Expiry columns are defined now; the filtering/sweep logic is sub-project #2.

**`score`** — the (profile, job) pairing
- PK = (`profile_id`, `job_id`) — scoping is via profile → user
- `overall` + six breakdown dims (`skills_match`, `seniority_fit`, `location_fit`,
  `language_fit`, `visa_friendly`, `growth_potential`), `reasoning`, `application_angle`,
  `status` (new | interested | applied | rejected | interview | offer),
  `applied`, `applied_at`, `scored_at`

**`application`** — generated documents
- `id` (PK), `profile_id` (FK), `job_id` (FK), `cv_optimized_md`, `cover_letter_md`,
  `gaps` (JSON), `status` (draft | sent | rejected | interview), `created_at`

**`pipeline_run`** — now actually scoped
- `id` (PK), `user_email` (FK), `profile_id` (FK), `mode`, `sources_run` (JSON),
  `jobs_fetched`, `jobs_new`, `jobs_scored`, `jobs_generated`, `status`, `error`,
  `started_at`, `finished_at`
- Fixes today's `candidate_id=""` bug.

### Seams left for later sub-projects (not built now)
- `user_llm_config`, `user_setting` (sub-project #4) hang off `user.email`.
- `source_health` (sub-project #3) is standalone.

## Identity flow & per-user scoping

**Identity resolution (no login):**
- `config.yaml` gains required top-level `user.email`.
- CLI: `--user <email>` overrides config; `jobradar init` prompts for it.
- Skill: `setup` / `run_pipeline` take a `user_email` arg.
- Resolution order: explicit flag/arg → config → clear error. No silent default / empty string.
- `_normalize_raw` still maps legacy keys (e.g. `candidate.cv_path`) and warns rather than
  hard-crashing on old configs.

**Threading through the pipeline:**
- `JobRadarPipeline.__init__(config, user_email)` resolves (or creates) the `user` row and
  that user's active `profile`. Every write (`score`, `application`, `pipeline_run`) carries
  `profile_id` / `user_email`.
- CV ingest is profile-versioned: ingesting a new CV creates a new `profile` version and
  flips `is_active`. The `cache_dir` JSON cache remains a parse cache keyed by CV hash.
- **Skip behavior (kept):** an already-scored `(profile_id, job_id)` pair is not re-scored.

**Read paths (the bug fix — all three updated together):**
- `api/routers/jobs.py` (`list_jobs`, `get_job`): take `user_email`, resolve active profile,
  `JOIN score ON score.profile_id = :profile_id`. No blended results; `get_job` returns the
  requested user's score, not `.first()`.
- `report/generator.py`: scoped to one user's active profile.
- `apply/engine.py`: `_load_eligible_jobs(profile_id, …)` instead of all scored rows. Also
  remove the blocking `input()` so the engine isn't CLI-only — move per-job confirmation to
  the caller via a callback.

**Job table stays global:** fetching is shared work; only scoring/applications/runs are
per-user. A job fetched for user A is reusable for user B (re-scored under B's profile),
keeping the scrape budget down.

## Infrastructure & folded-in cleanup

**Migrations (Alembic):**
- Add Alembic; the v1 schema is the initial migration.
- `init_db` becomes "run migrations to head" instead of `create_all`.
- From here, schema changes ship as migration scripts.

**Config:**
- `candidate.cv` moves under the active-profile concept; `config.yaml` gains required
  `user.email`. Legacy key mapping preserved with warnings.
- The hardcoded LLM probe (`env_probe.py`) stays as-is for now (single configured user still
  works); per-user catalog/custom config is sub-project #4.

**Cleanup folded in (only files we already touch):**
- `datetime.utcnow()` → `datetime.now(UTC)` in edited files (storage, pipeline).
- FastAPI dependency injection (`get_db` / `get_user`) to replace the repeated
  `cfg = get_config(); db_path = …; with next(get_session(...))` boilerplate in touched routers.
- Remove the dead `hasattr(cfg.search, 'quick_max_results')` branch in `pipeline.py`.
- Module-level imports for the function-level imports in edited files (`jobs.py`,
  `engine.py`, `pipeline.py`).
- Route every adapter ID through `normalizer.make_id` — fixes the non-deterministic
  `stepstone-{hash()}` IDs that silently break cross-run dedup.

Deferred to sub-project #5: CLI/skill dedup, the 400-char description truncation in scoring,
the `complete_auto` provider blocklist.

## Testing & verification

LLM is mocked throughout (fake `LLMClient`) so tests run in CI without keys.

- **Schema/migrations:** apply migrations to an empty SQLite; assert all six tables + keys
  exist; round-trip a `user → profile → score` insert.
- **Scoping (core correctness):** seed two users with active profiles and overlapping jobs;
  assert `list_jobs(user_A)` returns only A's scores, `get_job` returns the requested user's
  score (not `.first()`), and `_load_eligible_jobs(profile_A)` excludes B's rows.
- **Identity resolution:** flag > config > error precedence; missing email yields a clear
  error, not a silent `""`.
- **Profile versioning:** re-ingesting a CV creates v2 and flips `is_active`; v1 scores don't
  leak into v2 queries.
- **Skip behavior:** an already-scored `(profile, job)` pair is not re-scored.
- **CI:** updated to run `pytest tests/` (currently uses inline `python -c`).

## Risks

- **Discarding the old DB** is intentional and accepted (most rows expired). Users keep their
  `config.yaml`; only `jobradar.db` is recreated.
- **Required `user.email`** is a breaking config change. Mitigated by a clear error message
  and `jobradar init` prompting for it.
- **Read-path changes** are the highest-value but also highest-touch part; the scoping test
  suite is the guard.
