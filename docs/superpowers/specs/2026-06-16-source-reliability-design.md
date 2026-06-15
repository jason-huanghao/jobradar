# Source Reliability — Design Spec (sub-project #3)

**Status:** approved (PM-authored, autonomous)
**Date:** 2026-06-16
**Branch:** `refactor/source-reliability`
**Depends on:** #1 (foundation), #2 (expiry & freshness) — both merged to `main`.

## Problem

Job sources fail *silently*. Every adapter catches its own errors and returns `[]`
(`registry.py` also wraps each source in `try/except … return source_id, []`). The
pipeline logs `"Source X: 0 jobs"` and moves on. Consequences:

- A scraper that breaks (layout shift, 403/429 block, dependency missing) is
  indistinguishable from a source that legitimately had no matches.
- `PipelineRun.sources_run` exists in the schema but is **never populated** — there
  is no record of which sources ran, succeeded, or failed.
- No retry on transient failures.
- Operators (CLI/API) have no way to see source health.

The locked direction for #3 was: *hybrid (APIs where they exist + one hardened
Playwright crawler + per-source health signals)*.

## Scope decision (PM)

This PR delivers the **measurement & surfacing** layer — the actual reliability win,
and fully testable without network/browser:

- Per-source outcome classification (single source of truth).
- A typed `SourceError` so "blocked/failed" is distinguishable from "empty"; the two
  most fragile scrapers (StepStone, XING) raise it.
- Registry instrumentation: timing, bounded retry on transient `SourceError`, recorded
  outcomes.
- Persist outcomes to `PipelineRun.sources_run` (no migration — field already exists).
- Rolling per-source health aggregation read back from recent runs.
- Adapter `kind` taxonomy (`api` / `library` / `scraper`) — the explicit "hybrid" framing.
- Surfacing: `jobradar sources` CLI + `GET /api/sources`.

**Deferred to follow-up #3b (documented, not dropped): the hardened Playwright browser
crawler.** Rationale: instrument first — the health data then tells us *which* scraper
genuinely needs a browser. Introducing Playwright (browser binaries) into the pip-install
+ pytest CI is a disproportionate dependency/flakiness cost to carry before that data
exists. Sequencing: measure → identify worst source → replace just that one with a
browser crawler, on its own PR with its own CI considerations.

## Design

### 1. `sources/health.py` — single source of truth

```python
SourceStatus = Literal["ok", "empty", "error", "blocked"]

@dataclass
class SourceOutcome:
    source_id: str
    status: SourceStatus
    jobs: int
    duration_ms: int
    attempts: int = 1
    error: str = ""           # short message, truncated
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, d: dict) -> "SourceOutcome": ...

def classify(jobs: int, error: Exception | None) -> SourceStatus:
    # SourceError(blocked=True) -> "blocked"
    # any other error           -> "error"
    # no error, jobs == 0       -> "empty"
    # no error, jobs  > 0       -> "ok"
```

`status_is_failure(status)` helper → `status in {"error", "blocked"}` (used by rolling
health to count consecutive failures). Error messages truncated to 200 chars (consistent
with the codebase's existing truncation convention; see cleanup #5).

### 2. `SourceError` (in `sources/base.py`)

```python
class SourceError(Exception):
    def __init__(self, message: str, *, blocked: bool = False):
        super().__init__(message)
        self.blocked = blocked
```

- `JobSource` gains a class attribute `kind: str = "scraper"`.
- Adapters set `kind`: `arbeitsagentur = "api"`, `jobspy = "library"`, the rest stay
  `"scraper"` (default).
- StepStone & XING: replace `return []` on HTTP non-200 with
  `raise SourceError(..., blocked=status in (403, 429))`, and their top-level network
  `except` `return []` with `raise SourceError(...)`. **Per-query** failures inside a
  multi-query loop still continue (one bad query shouldn't fail the whole source); only a
  whole-source hard failure raises. Other adapters are unchanged in this PR (their
  silent-empty still shows up as `empty` streaks in rolling health).

### 3. Registry instrumentation (`sources/registry.py`)

- `fetch_all` keeps its `list[RawJob]` return (backward compatible — `test_foundation`
  monkeypatches it). It additionally populates `self.last_outcomes: list[SourceOutcome]`
  as a side effect.
- Each source runs through a retry wrapper: up to `max_attempts` attempts, retrying only
  on `SourceError`, with `retry_base_delay * 2**(n-1)` backoff. Non-`SourceError`
  exceptions are caught once (recorded as `error`, no retry — they are likely
  deterministic bugs, not transient).
- Timing via `time.monotonic()`. Outcome built via `classify()`.
- The existing `on_source_done(sid, count)` callback signature is preserved.

### 4. Persistence (`pipeline.py`)

After `fetch_all`, write `run_record.sources_run = json.dumps([o.to_dict() for o in
registry.last_outcomes])`. Set on the `PipelineRun` row that's already committed at the
end of `run()`. No schema change.

### 5. Rolling health (`storage/repo.py`)

```python
def recent_source_health(session, limit: int = 20) -> dict[str, dict]:
    # Read the last `limit` pipeline_run rows (newest first), parse sources_run JSON.
    # Per source_id, aggregate:
    #   last_status, last_jobs, last_run_at,
    #   consecutive_failures (from newest backwards until first non-failure),
    #   last_ok_at (most recent run where status == "ok")
```

Pure function over the session; tested directly by seeding `PipelineRun` rows.

### 6. Surfacing

- **CLI `jobradar sources`**: builds the registry from config (for `kind` + `enabled`),
  joins with `recent_source_health`. Rich table: source, kind, enabled, last status,
  last #jobs, consecutive failures, last-ok.
- **API `GET /api/sources`**: new router `api/routers/sources.py`, mounted at
  `/api/sources`. Returns `{"sources": [ {source_id, kind, enabled, last_status,
  last_jobs, consecutive_failures, last_ok_at} ]}`.

### 7. Config (`config.py`)

```python
class ReliabilityConfig(BaseModel):
    max_attempts: int = 2
    retry_base_delay: float = 0.5
# AppConfig.reliability: ReliabilityConfig
```

Registry reads `config.reliability`.

## Out of scope (this PR)

- Playwright browser crawler (→ #3b).
- Converting the CN scrapers / jobspy / arbeitsagentur to raise `SourceError` (their
  silent-empty is still captured as `empty`; convert later if health data shows it
  matters).
- Alerting/notifications on degraded sources.
- A dedicated `source_health` table (rolling health is derived from `pipeline_run`;
  a table is only warranted if we need history beyond recent runs).

## Success criteria

1. New `tests/test_source_reliability.py` covers: `classify` for all four statuses;
   `SourceOutcome` round-trip; registry records outcomes + retries on `SourceError` +
   does not retry on other exceptions; StepStone/XING raise `SourceError` on non-200
   (blocked on 403/429); pipeline persists `sources_run`; `recent_source_health`
   aggregation incl. consecutive-failure counting; `GET /api/sources` shape.
2. All pre-existing tests still pass (41 → 41+new).
3. `jobradar sources` runs against a fresh DB without error (empty health table).
4. Changed files ruff-clean (pre-existing debt untouched, per cleanup #5).
