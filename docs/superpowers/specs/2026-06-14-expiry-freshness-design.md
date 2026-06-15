# Expiry & Freshness — Design Spec

**Date:** 2026-06-14
**Sub-project:** #2 of the JobRadar refactor
**Status:** Approved (brainstormed 2026-06-14)
**Branch:** `refactor/expiry-freshness`

## Problem

The `job` table already carries three lifecycle columns — `valid_through`,
`expires_at`, and `status` (`active` | `expired`) — added in sub-project #1, but
**nothing writes or reads them**. They take their defaults (`""`, `""`,
`"active"`) on every insert and are ignored by every read path. As a result:

- Expired/stale jobs accumulate forever and surface in the API, the HTML report,
  and the apply engine as if they were live.
- The only freshness signal in the codebase is `hard_filter`'s in-memory
  `date_posted` cutoff, applied **before scoring** to `RawJob`s. It never touches
  persisted rows, and it ignores any explicit deadline the source provides.
- The write path inserts **new** jobs only; re-seen jobs are skipped entirely, so
  `last_seen_at` is frozen at first insert and cannot signal disappearance.

This sub-project wires the lifecycle columns end to end: capture deadlines,
refresh last-seen, sweep stale rows to `expired`, and hide expired rows from all
read paths by default.

## Goals

- A job is marked `expired` when **any** of three signals trips:
  1. **Explicit deadline** — the source's `validThrough` is in the past.
  2. **Posting age** — `date_posted + ttl` is in the past.
  3. **Disappearance** — `last_seen_at + staleness_window` is in the past
     (we stopped seeing it in fresh crawls).
- A reusable sweep runs **both** automatically (as a pipeline step) and as a
  standalone `jobradar sweep` command (cron-friendly).
- Read paths (API, report, apply engine) **hide expired jobs by default**, with
  an explicit `include_expired` opt-in. The apply engine never acts on expired
  jobs.
- Expired jobs are **flagged, never deleted** — all history (scores,
  applications) is preserved. Purging is explicitly out of scope (deferred to
  cleanup sub-project #5 if ever needed).
- One source of truth for the date math, shared between `hard_filter` (pre-score)
  and the sweep (post-persist).

## Non-Goals

- Hard-deleting or purging expired jobs (deferred to #5).
- Harvesting `validThrough` from every adapter — only the adapters that already
  parse JSON-LD (`stepstone`, `xing`) capture it; others leave it `""`.
- Any UI work beyond the existing API/report surfaces.
- Reconciling the two distinct `status` fields (`Job.status` =
  active/expired lifecycle vs. `Score.status` = per-user workflow). They remain
  separate; this spec only touches `Job.status`.

## Locked Decisions

1. **Expiry = OR of all three signals** (deadline, posting age, disappearance).
2. **Sweep runs both** automatically (pipeline step) and manually (`jobradar sweep`).
3. **Read paths hide expired by default**, with an `include_expired` opt-in;
   apply engine never acts on expired.
4. **Flag only, never delete.**
5. **Shared freshness helper**; `hard_filter` keeps its pre-scoring role.
6. **`expires_at` = objective deadline** (earliest of `validThrough` and
   `date_posted + ttl`), set at write time. The volatile disappearance signal
   lives only in the sweep and never churns the stored deadline (Approach A).

## Architecture

### Component 1 — Freshness module (single source of truth)

New file `src/jobradar/scoring/freshness.py`, sitting next to `hard_filter.py`,
holding pure functions usable on both `RawJob` and the persisted `Job`:

```python
def parse_date(s: str) -> datetime | None
    # Tolerant parse via dateutil (ignoretz=True). Empty/garbage -> None.

def compute_expires_at(date_posted: str, valid_through: str, ttl_days: int) -> str
    # Objective deadline as ISO string = EARLIEST of:
    #   - valid_through (if parseable)
    #   - date_posted + ttl_days (if date_posted parseable)
    # Returns "" if neither is known.

def is_expired(expires_at: str, last_seen_at: datetime, now: datetime,
               staleness_days: int) -> bool
    # True if (expires_at parseable and <= now)
    #      OR (last_seen_at + staleness_days <= now)

def is_too_old(date_posted: str, valid_through: str, now: datetime,
               ttl_days: int) -> bool
    # Pre-scoring check used by hard_filter:
    # True (drop) if date_posted parseable and < now - ttl_days,
    #             OR valid_through parseable and < now (already past).
```

`hard_filter._check` replaces its inline `dateutil` block with a call to
`freshness.is_too_old(date_posted, valid_through, now, cfg.search.max_days_old)`.
This is behavior-preserving for the posting-age case (the old code computed
`cutoff = now - max_days_old` once; `is_too_old` derives the same cutoff
internally) and **adds** honoring of an already-past `valid_through`. `now` is
captured once at the top of `hard_filter.apply` and threaded in. No other change
to `hard_filter`'s role.

All date parsing is tolerant: unparseable or empty values are treated as
"unknown" and never raise. A job with no `date_posted`, no `valid_through`, and a
recent `last_seen_at` stays `active`.

### Component 2 — Write path (capture + touch)

**Scrape model.** Add `valid_through: str = ""` to `RawJob`
(`src/jobradar/models/job.py`).

**Adapters.** `stepstone.py` and `xing.py` add
`valid_through=data.get("validThrough", "")` next to their existing
`date_posted` parse. Other adapters leave it `""`.

**Persist (`pipeline.py` Step 4)** changes from insert-only to **insert-or-touch**:

- **New jobs** (`j.id not in existing_ids`): set `valid_through=j.valid_through`
  and `expires_at=freshness.compute_expires_at(j.date_posted, j.valid_through,
  cfg.search.max_days_old)` at insert (previously left as defaults).
- **Re-seen jobs** (currently dropped on the floor): fetch the row and
  - set `last_seen_at = now`;
  - if the stored `valid_through` was empty and the fresh scrape now has one,
    fill it and recompute `expires_at`.

Refreshing `last_seen_at` on re-seen jobs is what makes the disappearance signal
meaningful.

### Component 3 — The sweep

New function in `src/jobradar/storage/repo.py`:

```python
def sweep_expired(session: Session, now: datetime, staleness_days: int) -> int:
    # Select status == "active" jobs; for each, freshness.is_expired(...);
    # flip matches to status="expired"; commit; return count flipped.
    # Flag only — never deletes. Idempotent.
```

Wired in two places:

- **Pipeline:** a new step at the **start** of a run (after the session opens,
  before fetch/score/read) so all reads within the same run see a clean set.
  Emits a `swept` event with the count.
- **CLI:** new `jobradar sweep --config <cfg> [--user <email>]` command that
  resolves the DB path, runs `sweep_expired`, and prints the count. Cron-friendly.
  The sweep is global/objective; `--user` is optional and used only for DB-path
  resolution consistency with the other commands.

### Component 4 — Read-side filtering

Single choke point: **`repo.list_scored`** is the only multi-row read used by the
jobs API, the report, and the apply engine.

```python
def list_scored(session, profile_id, min_score=0.0, include_expired=False):
    # default: add .where(Job.status != "expired")
```

Propagation:

- **API `GET /jobs`:** add `include_expired: bool = Query(default=False)`; pass
  through to `list_scored`.
- **API `GET /jobs/{id}`:** left as-is — a direct lookup by id that already
  returns the job's `status`. Showing one expired detail on explicit request is
  acceptable.
- **Report `load_report_jobs`:** inherits the filter via `list_scored`; expired
  jobs drop out of the HTML.
- **Apply engine `run_apply`:** inherits the filter via `list_scored`; never acts
  on expired jobs.

### Component 5 — Config

`SearchConfig` (`src/jobradar/config.py`):

- **Reuse** existing `max_days_old: int = 14` as the posting-age TTL — keeps a
  single freshness horizon shared between `hard_filter` and the sweep.
- **Add** one knob: `staleness_days: int = 7` (not re-seen in 7 days ⇒ expired).

## Data Flow

```
scrape (RawJob incl. valid_through)
   │
   ▼
pipeline run
   ├─ Step 0 (NEW): sweep_expired(now, staleness_days)   # flips stale active→expired
   ├─ fetch_all
   ├─ persist (insert-or-touch):
   │     new  → set valid_through, expires_at=compute_expires_at(...)
   │     seen → touch last_seen_at, backfill valid_through/expires_at
   ├─ hard_filter (uses freshness.is_too_old)            # pre-score drop
   ├─ score (unchanged)
   └─ generate (unchanged)

reads (API / report / apply) → list_scored(include_expired=False)
                                   → WHERE Job.status != 'expired'

standalone:  jobradar sweep  → sweep_expired(now, staleness_days)
```

## Error Handling

- Empty/unparseable dates are "unknown," never raise (mirrors hard_filter's
  current `except: pass` tolerance).
- A job with no date signals and a recent `last_seen_at` stays `active`.
- The sweep is idempotent and safe to re-run; SQLite's single-writer model makes
  concurrent reads during a sweep safe.
- No schema migration is required — all columns already exist from sub-project #1.

## Testing (TDD; no LLM involved)

- **`freshness.py` units:**
  - `compute_expires_at`: deadline = earliest of the two signals; `""` when both
    unknown; `valid_through`-only; `date_posted`-only.
  - `is_expired`: each signal independently trips, combined, and the all-unknown
    "stays active" case.
  - `is_too_old`: posting-age cutoff (preserves current behavior) + new
    already-past `valid_through` honoring.
- **`sweep_expired`:** seed active jobs that trip each signal → assert the right
  ones flip, count is correct, already-expired/active-fresh rows untouched, and a
  second run is a no-op (idempotent).
- **Write path:** a re-seen job refreshes `last_seen_at` and backfills
  `valid_through`/`expires_at`; a new job gets `expires_at` computed at insert.
- **Read path:** `list_scored` hides expired by default and returns them with
  `include_expired=True`.
- **API:** `GET /jobs` excludes expired by default and includes them with
  `?include_expired=true`.

Environment: tests run via `.venv/bin/python -m pytest tests/` (uv-created venv;
system python has no pip). `init_db` takes a **file path**, not a URL.

## Files Touched

| File | Change |
|------|--------|
| `src/jobradar/scoring/freshness.py` | **new** — date math source of truth |
| `src/jobradar/scoring/hard_filter.py` | call `freshness.is_too_old` |
| `src/jobradar/models/job.py` | add `valid_through` to `RawJob` |
| `src/jobradar/sources/adapters/stepstone.py` | capture `validThrough` |
| `src/jobradar/sources/adapters/xing.py` | capture `validThrough` |
| `src/jobradar/pipeline.py` | sweep step + insert-or-touch persist |
| `src/jobradar/storage/repo.py` | `sweep_expired` + `list_scored(include_expired)` |
| `src/jobradar/api/routers/jobs.py` | `include_expired` query param |
| `src/jobradar/interfaces/cli.py` | `jobradar sweep` command |
| `src/jobradar/config.py` | add `staleness_days` |
| `tests/` | new freshness/sweep/read tests |
