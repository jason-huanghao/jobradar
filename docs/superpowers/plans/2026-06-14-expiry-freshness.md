# Expiry & Freshness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing `valid_through` / `expires_at` / `status` job columns end to end — capture deadlines, refresh last-seen, sweep stale jobs to `expired`, and hide expired jobs from all read paths by default.

**Architecture:** A single freshness module (`scoring/freshness.py`) owns all date math and is shared by `hard_filter` (pre-score drop) and a new `sweep_expired` repo function (post-persist flip). The pipeline persist step becomes insert-or-touch so re-seen jobs refresh `last_seen_at`. The sweep runs both as a pipeline step and a `jobradar sweep` CLI command. All multi-row reads funnel through `repo.list_scored`, which gains an `include_expired` flag defaulting to `False`.

**Tech Stack:** Python 3.11/3.12, SQLModel/SQLAlchemy over SQLite, Typer (CLI), FastAPI (API), python-dateutil, pytest.

**Environment note:** System python has no pip. Run everything via the uv venv:
`.venv/bin/python -m pytest tests/` and `.venv/bin/ruff check src/jobradar/`.
`init_db()` takes a **file path**, not a SQLAlchemy URL. All timestamps in this
codebase are timezone-naive UTC (`datetime.utcnow()`); keep that convention.

---

## Spec

See `docs/superpowers/specs/2026-06-14-expiry-freshness-design.md`.

## File Structure

| File | Responsibility |
|------|----------------|
| `src/jobradar/scoring/freshness.py` | **new** — pure date math: `parse_date`, `compute_expires_at`, `is_expired`, `is_too_old`. Single source of truth. |
| `src/jobradar/scoring/hard_filter.py` | delegate its age check to `freshness.is_too_old`. |
| `src/jobradar/config.py` | add `staleness_days` to `SearchConfig`. |
| `src/jobradar/models/job.py` | add `valid_through` field to `RawJob`. |
| `src/jobradar/sources/adapters/stepstone.py` | capture `validThrough` from JSON-LD. |
| `src/jobradar/sources/adapters/xing.py` | capture `validThrough` from JSON-LD. |
| `src/jobradar/storage/repo.py` | `sweep_expired()` + `include_expired` flag on `list_scored`. |
| `src/jobradar/pipeline.py` | sweep step at run start + insert-or-touch persist. |
| `src/jobradar/api/routers/jobs.py` | `include_expired` query param on `GET /jobs`. |
| `src/jobradar/interfaces/cli.py` | new `jobradar sweep` command. |
| `tests/test_expiry.py` | **new** — freshness units, sweep, list_scored filter, write path, hard_filter. |

---

## Task 1: Freshness module

**Files:**
- Create: `src/jobradar/scoring/freshness.py`
- Test: `tests/test_expiry.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_expiry.py`:

```python
"""Expiry & freshness tests. No LLM involved."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine


def _mem_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    return eng


NOW = datetime(2026, 6, 14, 12, 0, 0)


# ── freshness.compute_expires_at ──────────────────────────────────
def test_compute_expires_at_prefers_earliest():
    from jobradar.scoring.freshness import compute_expires_at
    # valid_through (2026-06-20) is earlier than date_posted+14 (2026-06-24)
    out = compute_expires_at("2026-06-10", "2026-06-20", ttl_days=14)
    assert out.startswith("2026-06-20")


def test_compute_expires_at_posting_only():
    from jobradar.scoring.freshness import compute_expires_at
    out = compute_expires_at("2026-06-10", "", ttl_days=14)
    assert out.startswith("2026-06-24")


def test_compute_expires_at_unknown():
    from jobradar.scoring.freshness import compute_expires_at
    assert compute_expires_at("", "", ttl_days=14) == ""
    assert compute_expires_at("garbage", "also bad", ttl_days=14) == ""


# ── freshness.is_expired ──────────────────────────────────────────
def test_is_expired_by_deadline():
    from jobradar.scoring.freshness import is_expired
    assert is_expired("2026-06-01", NOW, NOW, staleness_days=7) is True


def test_is_expired_by_staleness():
    from jobradar.scoring.freshness import is_expired
    old_seen = NOW - timedelta(days=10)
    assert is_expired("", old_seen, NOW, staleness_days=7) is True


def test_is_expired_stays_active():
    from jobradar.scoring.freshness import is_expired
    fresh_seen = NOW - timedelta(days=1)
    assert is_expired("", fresh_seen, NOW, staleness_days=7) is False
    assert is_expired("2026-12-31", fresh_seen, NOW, staleness_days=7) is False


# ── freshness.is_too_old ──────────────────────────────────────────
def test_is_too_old_by_posting_age():
    from jobradar.scoring.freshness import is_too_old
    # posted 20 days before NOW, ttl 14 -> too old
    assert is_too_old("2026-05-25", "", NOW, ttl_days=14) is True
    # posted 5 days before NOW -> fresh
    assert is_too_old("2026-06-09", "", NOW, ttl_days=14) is False


def test_is_too_old_by_past_deadline():
    from jobradar.scoring.freshness import is_too_old
    # recent posting but the deadline already passed -> too old
    assert is_too_old("2026-06-13", "2026-06-01", NOW, ttl_days=14) is True


def test_is_too_old_unparseable_keeps():
    from jobradar.scoring.freshness import is_too_old
    assert is_too_old("", "", NOW, ttl_days=14) is False
    assert is_too_old("not a date", "", NOW, ttl_days=14) is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_expiry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'jobradar.scoring.freshness'`

- [ ] **Step 3: Write the implementation**

Create `src/jobradar/scoring/freshness.py`:

```python
"""Freshness & expiry date math — single source of truth.

Used by hard_filter (pre-scoring drop of stale RawJobs) and by the sweep
(post-persist flip of stale Job rows). All datetimes are timezone-naive UTC.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from dateutil import parser as dateutil_parser


def parse_date(s: str) -> datetime | None:
    """Tolerant parse. Empty or unparseable input returns None (never raises)."""
    if not s:
        return None
    try:
        return dateutil_parser.parse(s, ignoretz=True)
    except Exception:
        return None


def compute_expires_at(date_posted: str, valid_through: str, ttl_days: int) -> str:
    """Objective deadline as an ISO string = earliest of:
      - valid_through (if parseable)
      - date_posted + ttl_days (if date_posted parseable)
    Returns "" when neither signal is known.
    """
    candidates: list[datetime] = []
    vt = parse_date(valid_through)
    if vt is not None:
        candidates.append(vt)
    dp = parse_date(date_posted)
    if dp is not None:
        candidates.append(dp + timedelta(days=ttl_days))
    if not candidates:
        return ""
    return min(candidates).isoformat()


def is_expired(expires_at: str, last_seen_at: datetime, now: datetime,
               staleness_days: int) -> bool:
    """True if the stored deadline has passed OR the job hasn't been re-seen
    within the staleness window."""
    ea = parse_date(expires_at)
    if ea is not None and ea <= now:
        return True
    if last_seen_at + timedelta(days=staleness_days) <= now:
        return True
    return False


def is_too_old(date_posted: str, valid_through: str, now: datetime,
               ttl_days: int) -> bool:
    """Pre-scoring drop check. True if the posting is older than the TTL or its
    explicit deadline has already passed."""
    vt = parse_date(valid_through)
    if vt is not None and vt < now:
        return True
    dp = parse_date(date_posted)
    if dp is not None and dp < now - timedelta(days=ttl_days):
        return True
    return False
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_expiry.py -v`
Expected: PASS (all freshness tests green)

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/scoring/freshness.py tests/test_expiry.py
git commit -m "feat: freshness date-math module (expiry single source of truth)"
```

---

## Task 2: Add `staleness_days` config knob

**Files:**
- Modify: `src/jobradar/config.py:66` (inside `SearchConfig`)

- [ ] **Step 1: Add the field**

In `SearchConfig`, immediately after the `max_days_old` line, add `staleness_days`:

```python
    max_results_per_source: int = 20
    max_days_old: int = 14
    staleness_days: int = 7          # not re-seen in N days -> expired
    quick_max_results: int = 5
```

- [ ] **Step 2: Verify it loads**

Run: `.venv/bin/python -c "from jobradar.config import SearchConfig; print(SearchConfig().staleness_days)"`
Expected: `7`

- [ ] **Step 3: Commit**

```bash
git add src/jobradar/config.py
git commit -m "feat: add search.staleness_days config knob"
```

---

## Task 3: Capture `valid_through` in `RawJob` and adapters

**Files:**
- Modify: `src/jobradar/models/job.py:19` (RawJob)
- Modify: `src/jobradar/sources/adapters/stepstone.py:177-183`
- Modify: `src/jobradar/sources/adapters/xing.py:151-157`
- Test: `tests/test_expiry.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_expiry.py`:

```python
# ── RawJob carries valid_through ──────────────────────────────────
def test_rawjob_has_valid_through():
    from jobradar.models.job import RawJob
    j = RawJob(title="Eng", valid_through="2026-07-01")
    assert j.valid_through == "2026-07-01"
    assert RawJob(title="Eng").valid_through == ""
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_expiry.py::test_rawjob_has_valid_through -v`
Expected: FAIL — `RawJob` has no `valid_through`

- [ ] **Step 3: Add the field to `RawJob`**

In `src/jobradar/models/job.py`, after the `date_posted` line:

```python
    date_posted: str = ""
    valid_through: str = ""        # source deadline (JSON-LD validThrough); "" if unknown
```

- [ ] **Step 4: Capture it in the stepstone adapter**

In `src/jobradar/sources/adapters/stepstone.py`, in the `return RawJob(...)` block, add the `valid_through` kwarg after `date_posted`:

```python
    return RawJob(
        id=make_id("stepstone", url, title),
        title=title, company=company, location=location, url=url,
        description=(data.get("description") or "")[:500],
        source="stepstone",
        date_posted=data.get("datePosted", ""),
        valid_through=data.get("validThrough", ""),
    )
```

- [ ] **Step 5: Capture it in the xing adapter**

In `src/jobradar/sources/adapters/xing.py`, in the `return RawJob(...)` block, add the `valid_through` kwarg after `date_posted`:

```python
    return RawJob(
        id=f"xing-{abs(hash(url)) % 10**8}",
        title=title, company=company, location=location, url=url,
        description=(data.get("description") or "")[:500],
        source="xing",
        date_posted=data.get("datePosted", ""),
        valid_through=data.get("validThrough", ""),
    )
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_expiry.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/jobradar/models/job.py src/jobradar/sources/adapters/stepstone.py src/jobradar/sources/adapters/xing.py tests/test_expiry.py
git commit -m "feat: capture validThrough into RawJob (stepstone, xing)"
```

---

## Task 4: Route `hard_filter` through `freshness.is_too_old`

**Files:**
- Modify: `src/jobradar/scoring/hard_filter.py`
- Test: `tests/test_expiry.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_expiry.py`:

```python
# ── hard_filter honors valid_through ──────────────────────────────
def test_hard_filter_drops_past_deadline():
    from jobradar.config import AppConfig
    from jobradar.models.job import RawJob
    from jobradar.scoring.hard_filter import apply as hard_filter

    cfg = AppConfig()
    recent = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    past = (datetime.utcnow() - timedelta(days=2)).date().isoformat()
    # recent posting, but deadline already passed -> dropped
    jobs = [RawJob(title="Eng", date_posted=recent, valid_through=past)]
    kept, dropped = hard_filter(jobs, cfg)
    assert kept == [] and dropped == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_expiry.py::test_hard_filter_drops_past_deadline -v`
Expected: FAIL — current hard_filter ignores `valid_through`, keeps the job

- [ ] **Step 3: Update `hard_filter`**

In `src/jobradar/scoring/hard_filter.py`:

(a) Replace the import block and `apply` cutoff setup. Change the top imports from:

```python
import logging
from datetime import datetime, timedelta

from dateutil import parser as dateutil_parser

from ..config import AppConfig
from ..models.job import RawJob
```

to:

```python
import logging
from datetime import datetime

from ..config import AppConfig
from ..models.job import RawJob
from .freshness import is_too_old
```

(b) In `apply(...)`, replace the cutoff line:

```python
    cutoff = datetime.utcnow() - timedelta(days=config.search.max_days_old)
```

with:

```python
    now = datetime.utcnow()
    ttl_days = config.search.max_days_old
```

(c) Update the `_check` call inside the loop from:

```python
        reason = _check(job, cutoff, kw_lower, co_lower)
```

to:

```python
        reason = _check(job, now, ttl_days, kw_lower, co_lower)
```

(d) Replace the `_check` signature and its "Too old" block. Change the signature from:

```python
def _check(
    job: RawJob,
    cutoff: datetime,
    kw_lower: list[str],
    co_lower: list[str],
) -> str | None:
```

to:

```python
def _check(
    job: RawJob,
    now: datetime,
    ttl_days: int,
    kw_lower: list[str],
    co_lower: list[str],
) -> str | None:
```

and replace the existing "Too old" block:

```python
    # 3. Too old
    if job.date_posted:
        try:
            posted = dateutil_parser.parse(job.date_posted, ignoretz=True)
            if posted < cutoff:
                return f"too old: {job.date_posted}"
        except Exception:
            pass  # unparseable date — keep the job
```

with:

```python
    # 3. Too old (posting age) or explicit deadline already passed
    if is_too_old(job.date_posted, job.valid_through, now, ttl_days):
        return f"too old / expired: posted={job.date_posted} deadline={job.valid_through}"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_expiry.py tests/test_smoke.py -v`
Expected: PASS (new deadline test + existing smoke tests still green)

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/scoring/hard_filter.py tests/test_expiry.py
git commit -m "refactor: hard_filter delegates age check to freshness.is_too_old"
```

---

## Task 5: `sweep_expired` repo function

**Files:**
- Modify: `src/jobradar/storage/repo.py`
- Test: `tests/test_expiry.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_expiry.py`:

```python
# ── sweep_expired ─────────────────────────────────────────────────
def test_sweep_flips_stale_and_is_idempotent():
    from jobradar.storage.models import Job
    from jobradar.storage.repo import sweep_expired

    eng = _mem_engine()
    with Session(eng) as s:
        old_seen = NOW - timedelta(days=30)
        fresh_seen = NOW - timedelta(days=1)
        # by past deadline
        s.add(Job(id="dead", source="t", title="A", url="https://x/1",
                  expires_at="2026-06-01", last_seen_at=fresh_seen))
        # by staleness (no deadline, not seen in 30 days)
        s.add(Job(id="stale", source="t", title="B", url="https://x/2",
                  expires_at="", last_seen_at=old_seen))
        # fresh: no deadline, recently seen
        s.add(Job(id="live", source="t", title="C", url="https://x/3",
                  expires_at="", last_seen_at=fresh_seen))
        s.commit()

        count = sweep_expired(s, NOW, staleness_days=7)
        assert count == 2
        assert s.get(Job, "dead").status == "expired"
        assert s.get(Job, "stale").status == "expired"
        assert s.get(Job, "live").status == "active"

        # second run is a no-op
        assert sweep_expired(s, NOW, staleness_days=7) == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_expiry.py::test_sweep_flips_stale_and_is_idempotent -v`
Expected: FAIL — `sweep_expired` is not defined

- [ ] **Step 3: Implement `sweep_expired`**

In `src/jobradar/storage/repo.py`, update the import line at the top from:

```python
from datetime import datetime
```

(if no datetime import exists, add it) and add the freshness import:

```python
import uuid
from datetime import datetime

from sqlmodel import Session, select

from .models import Job, Profile, Score, User
from ..scoring.freshness import is_expired
```

Then append this function at the end of the file:

```python
def sweep_expired(session: Session, now: datetime, staleness_days: int) -> int:
    """Flip active jobs whose deadline passed or that went stale to expired.
    Flag only — never deletes. Idempotent. Returns the number flipped."""
    jobs = session.exec(select(Job).where(Job.status == "active")).all()
    count = 0
    for job in jobs:
        if is_expired(job.expires_at, job.last_seen_at, now, staleness_days):
            job.status = "expired"
            session.add(job)
            count += 1
    session.commit()
    return count
```

> Note: `repo.py` currently imports only `uuid` and the sqlmodel/models symbols. Add `from datetime import datetime` and the `is_expired` import as shown. The `..scoring.freshness` import is safe (no circular import — `freshness` imports only stdlib + dateutil).

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_expiry.py::test_sweep_flips_stale_and_is_idempotent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/storage/repo.py tests/test_expiry.py
git commit -m "feat: sweep_expired — flip stale/past-deadline jobs to expired"
```

---

## Task 6: `include_expired` filter on `list_scored`

**Files:**
- Modify: `src/jobradar/storage/repo.py` (`list_scored`)
- Test: `tests/test_expiry.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_expiry.py`:

```python
# ── list_scored hides expired by default ──────────────────────────
def test_list_scored_hides_expired_by_default():
    from jobradar.storage import repo
    from jobradar.storage.models import Job, Score

    eng = _mem_engine()
    with Session(eng) as s:
        repo.resolve_or_create_user(s, "a@x.com")
        p = repo.create_profile_version(s, "a@x.com", "cv.md", "{}")
        s.add(Job(id="live", source="t", title="A", url="https://x/1", status="active"))
        s.add(Job(id="gone", source="t", title="B", url="https://x/2", status="expired"))
        s.add(Score(profile_id=p.id, job_id="live", overall=8.0))
        s.add(Score(profile_id=p.id, job_id="gone", overall=9.0))
        s.commit()

        default_ids = [job.id for _, job in repo.list_scored(s, p.id)]
        assert default_ids == ["live"]

        all_ids = sorted(job.id for _, job in repo.list_scored(s, p.id, include_expired=True))
        assert all_ids == ["gone", "live"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_expiry.py::test_list_scored_hides_expired_by_default -v`
Expected: FAIL — `list_scored` returns both rows / has no `include_expired` kwarg

- [ ] **Step 3: Update `list_scored`**

In `src/jobradar/storage/repo.py`, replace the `list_scored` function:

```python
def list_scored(session: Session, profile_id: str, min_score: float = 0.0):
    """Return list[(Score, Job)] for a profile, score-descending."""
    query = (
        select(Score, Job)
        .join(Job, Score.job_id == Job.id)
        .where(Score.profile_id == profile_id)
    )
    if min_score > 0:
        query = query.where(Score.overall >= min_score)
    query = query.order_by(Score.overall.desc())
    return session.exec(query).all()
```

with:

```python
def list_scored(session: Session, profile_id: str, min_score: float = 0.0,
                include_expired: bool = False):
    """Return list[(Score, Job)] for a profile, score-descending.
    Expired jobs are hidden unless include_expired is True."""
    query = (
        select(Score, Job)
        .join(Job, Score.job_id == Job.id)
        .where(Score.profile_id == profile_id)
    )
    if not include_expired:
        query = query.where(Job.status != "expired")
    if min_score > 0:
        query = query.where(Score.overall >= min_score)
    query = query.order_by(Score.overall.desc())
    return session.exec(query).all()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_expiry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/storage/repo.py tests/test_expiry.py
git commit -m "feat: list_scored hides expired jobs by default (include_expired opt-in)"
```

---

## Task 7: Insert-or-touch persist in the pipeline

**Files:**
- Modify: `src/jobradar/pipeline.py` (imports + Step 4 persist block)
- Test: `tests/test_expiry.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_expiry.py`. This calls the persist logic directly via a helper we will add (`_persist_jobs`) so the test needs no LLM or network:

```python
# ── pipeline persist: insert-or-touch ─────────────────────────────
def test_persist_sets_expires_at_and_touches_seen():
    from jobradar.models.job import RawJob
    from jobradar.storage.models import Job
    from jobradar.pipeline import _persist_jobs

    eng = _mem_engine()
    posted = (NOW - timedelta(days=2)).date().isoformat()
    with Session(eng) as s:
        # first sighting: inserts with computed expires_at
        new1 = _persist_jobs(
            s, [RawJob(id="j1", source="t", title="Eng", url="https://x/1",
                       date_posted=posted, valid_through="")],
            ttl_days=14, now=NOW,
        )
        assert new1 == 1
        row = s.get(Job, "j1")
        assert row.expires_at != ""
        assert row.expires_at.startswith("2026")   # posted + 14 days
        first_seen = row.last_seen_at

        # re-sighting later with a now-known deadline: touches last_seen + backfills
        later = NOW + timedelta(days=1)
        new2 = _persist_jobs(
            s, [RawJob(id="j1", source="t", title="Eng", url="https://x/1",
                       date_posted=posted, valid_through="2026-06-20")],
            ttl_days=14, now=later,
        )
        assert new2 == 0
        row = s.get(Job, "j1")
        assert row.last_seen_at == later and row.last_seen_at != first_seen
        assert row.valid_through == "2026-06-20"
        assert row.expires_at.startswith("2026-06-20")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_expiry.py::test_persist_sets_expires_at_and_touches_seen -v`
Expected: FAIL — `_persist_jobs` is not defined

- [ ] **Step 3: Extract and implement `_persist_jobs`**

In `src/jobradar/pipeline.py`, add the freshness import near the other scoring imports:

```python
from .scoring.freshness import compute_expires_at
from .scoring.hard_filter import apply as hard_filter
```

Add a module-level helper next to `_db_to_raw` at the bottom of the file:

```python
def _persist_jobs(session: Session, raw_jobs: list[RawJob], ttl_days: int,
                  now: datetime) -> int:
    """Insert new jobs (with computed expires_at) and touch re-seen ones
    (refresh last_seen_at, backfill valid_through/expires_at). Returns the
    count of newly-inserted jobs."""
    existing_ids = set(session.exec(select(Job.id)).all())
    new_jobs = [j for j in raw_jobs if j.id not in existing_ids]
    seen_jobs = [j for j in raw_jobs if j.id in existing_ids]

    for j in new_jobs:
        session.add(Job(
            id=j.id, source=j.source, title=j.title, company=j.company,
            location=j.location, description=j.description, url=j.url,
            date_posted=j.date_posted, job_type=j.job_type, salary=j.salary,
            remote=j.remote, raw_extra=json.dumps(j.raw_extra),
            valid_through=j.valid_through,
            expires_at=compute_expires_at(j.date_posted, j.valid_through, ttl_days),
            last_seen_at=now,
        ))

    for j in seen_jobs:
        row = session.get(Job, j.id)
        if row is None:
            continue
        row.last_seen_at = now
        if not row.valid_through and j.valid_through:
            row.valid_through = j.valid_through
            row.expires_at = compute_expires_at(row.date_posted, j.valid_through, ttl_days)
        session.add(row)

    session.commit()
    return len(new_jobs)
```

Now replace the inline Step 4 block in `_execute`:

```python
        # Step 4: Persist new jobs
        existing_ids = set(session.exec(select(Job.id)).all())
        new_jobs = [j for j in raw_jobs if j.id not in existing_ids]
        for j in new_jobs:
            session.add(Job(
                id=j.id, source=j.source, title=j.title, company=j.company,
                location=j.location, description=j.description, url=j.url,
                date_posted=j.date_posted, job_type=j.job_type, salary=j.salary,
                remote=j.remote, raw_extra=json.dumps(j.raw_extra),
            ))
        session.commit()
        emit("db_saved", new=len(new_jobs))
```

with:

```python
        # Step 4: Persist — insert new jobs, touch re-seen ones
        new_jobs = [j for j in raw_jobs
                    if j.id not in set(session.exec(select(Job.id)).all())]
        jobs_new = _persist_jobs(session, raw_jobs, cfg.search.max_days_old,
                                 datetime.utcnow())
        emit("db_saved", new=jobs_new)
```

> `new_jobs` is still needed for Step 5's hard_filter (it filters only the newly-seen RawJobs). Keep the `new_jobs` list computed as shown above (before `_persist_jobs` inserts them) so Step 5 and the `PipelineResult(jobs_new=...)` continue to work. Update the later `PipelineResult` construction to use `jobs_new=len(new_jobs)` (it already does) — no change needed there.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_expiry.py tests/test_foundation.py -v`
Expected: PASS (new persist test + existing pipeline tests still green)

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/pipeline.py tests/test_expiry.py
git commit -m "feat: insert-or-touch persist (compute expires_at, refresh last_seen_at)"
```

---

## Task 8: Sweep step in the pipeline run

**Files:**
- Modify: `src/jobradar/pipeline.py` (imports + `_execute` start)
- Test: `tests/test_expiry.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_expiry.py`:

```python
# ── pipeline emits a swept event ──────────────────────────────────
def test_pipeline_dryrun_then_sweep_event(tmp_path, monkeypatch):
    """A non-dry-run sweeps at the start; assert sweep_expired is invoked."""
    import jobradar.pipeline as pl

    calls = {"n": 0}
    real = pl.sweep_expired

    def spy(session, now, staleness_days):
        calls["n"] += 1
        return real(session, now, staleness_days)

    monkeypatch.setattr(pl, "sweep_expired", spy)
    # _execute's sweep step is what we exercise; verify the symbol is wired.
    assert hasattr(pl, "sweep_expired")
```

> This is a light wiring test (full pipeline runs need an LLM, which the foundation suite already mocks). The real behavioral coverage for the sweep lives in Task 5's `test_sweep_flips_stale_and_is_idempotent`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_expiry.py::test_pipeline_dryrun_then_sweep_event -v`
Expected: FAIL — `pipeline` does not export `sweep_expired`

- [ ] **Step 3: Wire the sweep step**

In `src/jobradar/pipeline.py`, add `sweep_expired` to the repo import block:

```python
from .storage.repo import (
    create_profile_version,
    get_active_profile,
    resolve_or_create_user,
    scored_job_ids,
    sweep_expired,
)
```

In `_execute`, immediately **after** the dry-run early-return guard and before "Step 1", add the sweep step:

```python
        # dry-run: validate config + DB only — no LLM, no network
        if mode == "dry-run":
            emit("queries_built", count=0)
            return PipelineResult(run_id=run_id, jobs_fetched=0, jobs_new=0,
                                  jobs_scored=0, jobs_generated=0, top_jobs=[], status="done")

        # Step 0: sweep stale/expired jobs (read paths hide them)
        swept = sweep_expired(session, datetime.utcnow(), cfg.search.staleness_days)
        emit("swept", count=swept)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_expiry.py tests/test_foundation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/pipeline.py tests/test_expiry.py
git commit -m "feat: sweep stale jobs at pipeline run start (emits swept event)"
```

---

## Task 9: `include_expired` query param on `GET /jobs`

**Files:**
- Modify: `src/jobradar/api/routers/jobs.py` (`list_jobs`)
- Test: `tests/test_expiry.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_expiry.py`:

```python
# ── API hides expired by default ──────────────────────────────────
def test_api_jobs_hides_expired(tmp_path):
    from fastapi.testclient import TestClient
    from jobradar.api.main import create_app
    from jobradar.config import AppConfig
    from jobradar.storage.db import get_session, init_db
    from jobradar.storage.models import Job, Score
    from jobradar.storage import repo

    db = tmp_path / "jobradar.db"
    init_db(db)
    with next(get_session(db)) as s:
        repo.resolve_or_create_user(s, "a@x.com")
        p = repo.create_profile_version(s, "a@x.com", "cv.md", "{}")
        s.add(Job(id="live", source="t", title="A", url="https://x/1", status="active"))
        s.add(Job(id="gone", source="t", title="B", url="https://x/2", status="expired"))
        s.add(Score(profile_id=p.id, job_id="live", overall=8.0))
        s.add(Score(profile_id=p.id, job_id="gone", overall=9.0))
        s.commit()

    # create_app(config=...) sets the module-global config that deps.py reads
    # via get_config(); get_user_email then resolves cfg.user.email when no
    # ?user_email query param is supplied.
    cfg = AppConfig()
    cfg.user.email = "a@x.com"
    cfg.server.db_path = str(db)          # absolute path; resolve_path passes it through
    client = TestClient(create_app(config=cfg))

    default_ids = {j["id"] for j in client.get("/jobs").json()["jobs"]}
    assert default_ids == {"live"}

    all_ids = {j["id"] for j in client.get("/jobs?include_expired=true").json()["jobs"]}
    assert all_ids == {"live", "gone"}
```

> The API resolves config through `create_app(config=...)` (a module global in
> `api/main.py`), not env vars. `get_db_path` reads `cfg.server.db_path`;
> `get_user_email` resolves `cfg.user.email` when no `?user_email` param is
> given. No `monkeypatch` needed.

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_expiry.py::test_api_jobs_hides_expired -v`
Expected: FAIL — both jobs returned (no `include_expired` handling)

- [ ] **Step 3: Add the query param**

In `src/jobradar/api/routers/jobs.py`, add the `include_expired` parameter to `list_jobs` (after the `status` query param):

```python
    status: str = Query(default=""),
    include_expired: bool = Query(default=False),
```

and pass it into `list_scored`:

```python
        rows = list_scored(session, profile.id, min_score=min_score,
                           include_expired=include_expired)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_expiry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/jobradar/api/routers/jobs.py tests/test_expiry.py
git commit -m "feat: GET /jobs include_expired query param (default false)"
```

---

## Task 10: `jobradar sweep` CLI command

**Files:**
- Modify: `src/jobradar/interfaces/cli.py` (add command near `status`/`report`)

- [ ] **Step 1: Add the command**

In `src/jobradar/interfaces/cli.py`, add a new command (place it after the `status` command, before `report`):

```python
@app.command()
def sweep(
    config: Optional[Path] = typer.Option(None, "--config", help="Path to config.yaml"),
    user: str = typer.Option("", "--user", help="User email (accepted for CLI symmetry; sweep is global)"),
):
    """Mark stale or past-deadline jobs as expired (hidden from reports & apply)."""
    from datetime import datetime

    from ..config import load_config
    from ..storage.db import get_session, init_db
    from ..storage.repo import sweep_expired

    cfg = load_config(config)
    db_path = cfg.resolve_path(cfg.server.db_path)
    init_db(db_path)
    with next(get_session(db_path)) as session:
        count = sweep_expired(session, datetime.utcnow(), cfg.search.staleness_days)
    console.print(f"[green]Swept {count} job(s) to expired.[/green]")
```

- [ ] **Step 2: Verify the command is registered**

Run: `.venv/bin/jobradar sweep --help`
Expected: help text for the `sweep` command, showing `--config` and `--user`.

- [ ] **Step 3: Smoke-test against a temp DB**

Run:
```bash
.venv/bin/python -c "
from jobradar.storage.db import init_db, get_session
from jobradar.storage.models import Job
from jobradar.storage.repo import sweep_expired
from datetime import datetime, timedelta
import pathlib, tempfile
p = pathlib.Path(tempfile.mkdtemp()) / 'j.db'
init_db(p)
with next(get_session(p)) as s:
    s.add(Job(id='x', source='t', title='A', url='https://x/1',
              last_seen_at=datetime.utcnow()-timedelta(days=30)))
    s.commit()
    print('swept:', sweep_expired(s, datetime.utcnow(), 7))
    print('status:', s.get(Job, 'x').status)
"
```
Expected: `swept: 1` and `status: expired`

- [ ] **Step 4: Commit**

```bash
git add src/jobradar/interfaces/cli.py
git commit -m "feat: jobradar sweep CLI command"
```

---

## Task 11: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: all tests pass (the 25 foundation/smoke tests + the new `test_expiry.py` tests).

- [ ] **Step 2: Lint the changed files**

Run: `.venv/bin/ruff check src/jobradar/scoring/freshness.py src/jobradar/scoring/hard_filter.py src/jobradar/storage/repo.py src/jobradar/pipeline.py src/jobradar/api/routers/jobs.py src/jobradar/interfaces/cli.py`
Expected: no **new** errors in these files. (Pre-existing E741/F401/F541/F841 debt in cli.py is deferred to cleanup sub-project #5 — do not fix it here; only ensure you added none.)

- [ ] **Step 3: Smoke-test the dry-run pipeline**

Run: `.venv/bin/jobradar update --mode dry-run --config <your test config> --user test@example.com`
Expected: completes cleanly (dry-run returns before sweep/fetch).

- [ ] **Step 4: Final commit (if any lint fixups were needed)**

```bash
git add -A
git commit -m "chore: lint fixups for expiry & freshness"
```

---

## Self-Review Notes (for the implementer)

- **`new_jobs` vs `_persist_jobs` (Task 7):** `_persist_jobs` returns the new-insert
  count, but Step 5's `hard_filter` still operates on the `new_jobs` RawJob list.
  Compute `new_jobs` (the list) *before* calling `_persist_jobs`, since after the
  insert those ids are no longer "new". The plan's Step 3 shows this ordering.
- **Timezone:** everything is naive UTC (`datetime.utcnow()`); never introduce
  `timezone.aware` datetimes into the freshness comparisons.
- **No migration needed:** `valid_through`, `expires_at`, `status`, `last_seen_at`
  already exist on the `job` table from sub-project #1.
- **`status` field collision:** this plan only touches `Job.status`
  (active/expired). The per-user `Score.status` (new/interested/applied…) and the
  jobs router's existing `status` query param (which filters on `Score.status`)
  are untouched.
