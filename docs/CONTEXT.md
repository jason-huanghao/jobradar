# JobRadar — Project Context for Continuation Sessions

> **Read this first in any new session.**
> This document gives a new Claude session everything needed to continue working on JobRadar
> without re-reading the full codebase.

---

## Identity

| Field | Value |
|-------|-------|
| Package name | `openclaw-jobradar` v0.2.0 |
| Local path | `/Users/jason/Documents/Project/JobRadar` |
| GitHub | https://github.com/jason-huanghao/jobradar |
| Venv | `.venv/bin/python` (Python 3.14, all deps installed) |
| Run commands | `cd .../JobRadar && .venv/bin/jobradar ...` or `PYTHONPATH=src .venv/bin/python ...` |
| LLM key | `ARK_API_KEY` in `.env` (Volcengine Ark, `doubao-seed-2.0-code`) |
| CV | `cv/cv_current.md` (Hao Huang, PhD candidate, AI/ML/KG) |
| DB | `jobradar.db` (SQLite, ~800+ jobs already scraped) |
| Cache | `memory/` (profile JSON cached here) |

---

## What This Project Does

JobRadar is an **AI-powered job search agent** that:
1. Scrapes job listings from multiple sources (Arbeitsagentur, StepStone, XING, Indeed, Google Jobs, BOSS直聘, 拉勾, 智联)
2. Scores them 0–10 against the user's CV using an LLM (6 dimensions)
3. Generates tailored CV sections + cover letters for top matches
4. Exposes a web dashboard (Alpine.js SPA) and a FastAPI backend
5. Works as an **OpenClaw AI skill** — agents can configure and run it via tool calls

---

## Architecture

```
src/jobradar/
├── config.py           AppConfig (YAML + .env), all sub-configs
├── utils.py            profile_id() — sha256 of CandidateProfile
├── pipeline.py         JobRadarPipeline.run(mode, on_progress) — 7-step orchestrator
├── models/
│   ├── candidate.py    CandidateProfile (Pydantic)
│   └── job.py          RawJob, ScoredJob, SearchQuery, ScoreBreakdown
├── storage/
│   ├── db.py           SQLite via SQLModel, auto-mkdir on init_db()
│   └── models.py       Job, ScoredJobRecord, ApplicationRecord, PipelineRun, Candidate
├── profile/
│   ├── ingestor.py     ingest(source, llm, cache_dir) → CandidateProfile
│   ├── extractor.py    LLM extraction via cv_extract.jinja2; caches by sha256(cv_text)
│   │                   IMPORTANT: uses max_tokens=8192, has _recover_partial_json() fallback
│   └── readers/        FileAndUrlReader (PDF, DOCX, MD, TXT, HTTP URL)
├── sources/
│   ├── base.py         JobSource ABC: fetch(queries, since) + is_enabled(config)
│   ├── normalizer.py   make_id=sha256(source+url)[:16], normalise(), dedup()
│   ├── query_builder.py build_queries(profile, config, max_results_override=None)
│   │                   IMPORTANT: ALL queries carry max_results in extra{} via eu_extra()
│   ├── registry.py     SourceRegistry.fetch_all() parallel via ThreadPoolExecutor(6)
│   └── adapters/
│       ├── arbeitsagentur.py  BA REST API, 2-phase list+detail, 8 concurrent workers
│       ├── stepstone.py       Real HTML scraper (httpx+BS4), 3-strategy parse
│       ├── xing.py            Real HTML scraper (httpx+BS4), 3-strategy parse
│       ├── jobspy_adapter.py  python-jobspy wrapper (Indeed, Google Jobs)
│       ├── zhilian.py         REST API + Playwright XHR fallback
│       ├── lagou.py           3-strategy cascade: mobile API → AJAX → Playwright stealth
│       └── bosszhipin.py      Cookie auth + Playwright capture CLI
├── scoring/
│   ├── hard_filter.py   Pre-LLM filter: excluded keywords/companies, date cutoff
│   ├── scorer.py        score_jobs(jobs, profile, llm, batch_size, on_batch_done)
│   └── generator/
│       ├── cv_optimizer.py    optimize_cv(job, profile, llm) → (cv_md, gaps)
│       └── cover_letter.py    generate_cover_letter(scored_job, profile, llm) → md
├── api/
│   ├── main.py          FastAPI factory create_app(cfg), CORS, static mount
│   ├── ws.py            WebSocket /ws/pipeline — live progress streaming
│   ├── routers/         profile, jobs, pipeline, generate, outputs (5 routers)
│   └── static/index.html  Alpine.js SPA dashboard
├── interfaces/
│   ├── cli.py           Typer: init, update [--mode] [--limit], web, status, health,
│   │                    setup, install-agent
│   └── skill.py         OpenClaw HTTP wrapper (run_skill entry point + setup tool)
└── llm/
    ├── client.py        LLMClient: complete(), complete_auto(), batch()
    ├── env_probe.py     probe_llm_env() → auto-detects 10 providers
    └── prompts/         cv_extract.jinja2, job_score.jinja2, cv_optimize.jinja2,
                         cover_letter.jinja2
```

### Pipeline flow (7 steps)

```
CV file → profile extraction (LLM, cached) →
query builder (per-source SearchQuery list) →
parallel source fetch (ThreadPoolExecutor) →
dedup + hard filter →
LLM scoring (batched, incremental, skips already-scored) →
CV optimizer + cover letter for top-N →
SQLite persist
```

---

## Key Config Fields (config.yaml / AppConfig)

| Field | Default | Notes |
|-------|---------|-------|
| `candidate.cv_path` | `./cv/cv_current.md` | Also supports `.pdf`, `.docx`, `.txt`, URL |
| `llm.text.provider` | `volcengine` | Auto-detected from env |
| `llm.text.model` | `doubao-seed-2.0-code` | |
| `search.locations` | `[Hannover, Berlin, Hamburg, Remote]` | |
| `search.max_results_per_source` | `50` | Per source per query (full mode) |
| `search.quick_max_results` | `5` | Per source per query (quick mode) |
| `search.max_days_old` | `14` | |
| `search.exclude_keywords` | `[Praktikum, Werkstudent, internship, Ausbildung]` | |
| `sources.arbeitsagentur.enabled` | `true` | |
| `sources.jobspy.enabled` | `true` | boards: [indeed, google] |
| `sources.stepstone.enabled` | `true` | Real HTML scraper |
| `sources.xing.enabled` | `true` | Real HTML scraper |
| `sources.bosszhipin/lagou/zhilian.enabled` | `false` | CN, needs setup |
| `scoring.min_score_application` | `7.0` | Auto-generate docs above this |
| `server.port` | `7842` | |
| `server.db_path` | `./jobradar.db` | |
| `server.cache_dir` | `./memory` | Profile JSON cached here |

---

## CLI Reference

```bash
cd /Users/jason/Documents/Project/JobRadar

jobradar init                            # Interactive setup wizard (key + CV + locations)
jobradar health                          # LLM ping + CV file check
jobradar status                          # DB stats (jobs count, scored count)
jobradar update --mode dry-run           # Config check, no network
jobradar update --mode quick --limit 3   # Fast smoke test (~40 jobs, ~3 min)
jobradar update --mode full              # Daily run
jobradar web                             # Dashboard at http://localhost:7842
jobradar install-agent                   # macOS launchd daily agent at 08:00
```

---

## OpenClaw Skill Interface

**Entry point:** `jobradar.interfaces.skill:run_skill`

**Tools:**

| Tool | Purpose |
|------|---------|
| `setup` | Configure JobRadar without a server. Auto-detects OPENCLAW_API_KEY, ARK_API_KEY, ZAI_API_KEY etc. Accepts `api_key`, `cv_path`, `cv_content`, `locations`, `check_only` |
| `run_pipeline` | Fetch + score + generate. Params: `mode` (quick/full/score-only/dry-run) |
| `list_jobs` | Top-scoring jobs. Params: `min_score`, `source`, `limit` |
| `get_job_detail` | Full description by `job_id` |
| `generate_application` | CV + cover letter by `job_id` |
| `get_digest` | Markdown digest of top jobs |
| `get_status` | Last pipeline run status |

**Agent flow (3 user messages):**
```
1. setup({})                       → returns prompt_for_user (show it verbatim)
2. setup({"cv_path": "..."})       → returns configured=True
3. run_pipeline({"mode": "quick"}) → shows top matches
```

**Key behaviours of `setup` tool:**
- `check_only=True` → returns detected state + `prompt_for_user` without writing
- GitHub blob URLs auto-converted to raw format for download
- Default locations: Germany-wide 11 cities (Berlin, Hamburg, Munich, Frankfurt,
  Hannover, Cologne, Stuttgart, Leipzig, Dresden, Nuremberg, Remote)
- Returns `prompt_for_user` field — agent should show this verbatim to user
- `_MINIMAL_CONFIG` embedded in skill.py as fallback when no config.example.yaml

**Location detection uses scoped regex** (important — global regex would pick up exclude_keywords):
```python
re.search(r'locations:\s*\n((?:    - [^\n]+\n)*)', cfg_content)
```

---

## LLM Provider Auto-Detection Priority

Checked in this order (first found wins):
1. `OPENCLAW_API_KEY` → Z.AI proxy (`api.z.ai/v1`, `claude-sonnet-4-20250514`)
2. `ARK_API_KEY` → Volcengine Ark (`doubao-seed-2.0-code`)
3. `ZAI_API_KEY` → Z.AI (`claude-sonnet-4-20250514`)
4. `OPENAI_API_KEY` → OpenAI (`gpt-4o-mini`)
5. `ANTHROPIC_API_KEY` → Anthropic (`claude-sonnet-4-20250514`)
6. `DEEPSEEK_API_KEY` → DeepSeek (`deepseek-chat`)
7. `OPENROUTER_API_KEY` → OpenRouter
8. Ollama local (`localhost:11434`)
9. LM Studio local (`localhost:1234`)

---

## Known Issues / Current Limitations

| # | Issue | Status |
|---|-------|--------|
| 1 | Arbeitsagentur returns 403 intermittently from CI/shared IPs | Non-fatal; CI test is advisory (`continue-on-error: true`) |
| 2 | Lagou: CAPTCHA blocks all 3 strategies outside mainland China | Expected; mobile API + AJAX + Playwright all blocked |
| 3 | BossZhipin: requires manual cookie capture | Run `python -m jobradar.sources.adapters.bosszhipin --capture-cookies` |
| 4 | XING company field often empty (no structured data in HTML) | Cosmetic only |
| 5 | `tests/` directory is empty | CI uses inline `python -c` tests instead |
| 6 | venv pip can break after macOS Python upgrade | Fix: `rm -rf .venv && python3 -m venv .venv && .venv/bin/pip install -e ".[all]"` |

---

## CI Status

**File:** `.github/workflows/ci.yml`
**Runs on:** Python 3.11 + 3.12, ubuntu-latest

**Test steps:**
1. Import check (all modules including skill.py)
2. Lint (ruff, non-blocking)
3. DB init + auto-mkdir
4. Normaliser + dedup
5. Hard filter (Praktikum dropped)
6. Query builder max_results propagation
7. JSON truncation recovery (3 cases)
8. Skill setup tool (cv_content, locations, check_only)
9. dry-run pipeline
10. Arbeitsagentur connectivity (advisory, `continue-on-error: true`)
11. CLI smoke (`jobradar --help`, `jobradar status`)

**Current CI status:** ✅ Green (SHA `09f195779a50`)

---

## Recent Git Log

```
09f1957  fix(skill+extractor): minimal-turn UX, locations fix, JSON recovery
fbba716  fix(ci): make Arbeitsagentur live test advisory, add skill/filter/query tests
5fc1ee0  feat(skill): OpenClaw-native setup tool + API key auto-detection
4967119  fix(scoring): prevent JSON truncation on large batches
f80a166  fix: fresh-install correctness — limit flag, health cmd, SKILL.md rewrite
3e0ae49  feat(sources): port all 7 adapters from v1.0 — StepStone/XING real scrapers
59aa0d7  feat: v2 big-bang rewrite — modular pipeline, FastAPI dashboard, OpenClaw skill
```

---

## Verified End-to-End Results

**Fresh GitHub install → pipeline run:**
```
git clone https://github.com/jason-huanghao/jobradar.git && cd jobradar
pip install -e ".[all]"
cp config.example.yaml config.yaml   # edit CV path + API key
jobradar health                       # ✅ LLM ping OK
jobradar update --mode quick --limit 3
# → fetched: 41, scored: 33, generated: 4 ✅
```

**OpenClaw integration test result (actual interaction):**
```
User: install this skill → SKILL.md URL
OpenClaw: setup({}) → detects ARK_API_KEY, asks for CV only
User: https://github.com/jason-huanghao/daily-rss-digest/blob/main/cv_current.md
OpenClaw: setup({"cv_path": "..."}) → configured=True
OpenClaw: run_pipeline({"mode": "quick"}) → 41 fetched, 37 scored
Top match: Product Manager @ Nucs AI (Berlin) — Score: 9.0/10
```

---

## Possible Next Tasks

- [ ] **pytest unit tests** — `tests/` is empty; write real test files instead of CI inline scripts
- [ ] **XING company enrichment** — add detail-fetch step to get company name from job page
- [ ] **Feedback loop** — user marks applied/rejected → re-weights scorer prompts
- [ ] **StepStone pagination** — currently only fetches 2 pages; add more for `max_results > 50`
- [ ] **Email digest** — `EmailConfig` exists, notifier not wired up
- [ ] **Docker** — containerise for portable deployment
- [ ] **Dashboard screenshots** — add to README
- [ ] **Version bump** — bump to 0.2.1 after recent bug fixes
- [ ] **`jobradar init` non-interactive** — test `--yes` flag flow end-to-end
- [ ] **LinkedIn PDF** — `FileAndUrlReader` can read PDF; add instructions for LinkedIn export
- [ ] **Multiple candidate profiles** — currently single-user; add profile switching
- [ ] **Score history** — track score changes over time for the same job

---

## File Locations Quick Reference

| Purpose | Path |
|---------|------|
| Main config | `config.yaml` (gitignored, user-created) |
| Config template | `config.example.yaml` |
| LLM API keys | `.env` (gitignored) |
| SQLite database | `jobradar.db` |
| Cached CV profile | `memory/candidate_profile.json` |
| CV file | `cv/cv_current.md` (or .pdf/.docx) |
| LLM prompt templates | `src/jobradar/llm/prompts/*.jinja2` |
| Skill entry point | `src/jobradar/interfaces/skill.py:run_skill` |
| CLI entry point | `src/jobradar/interfaces/cli.py:main` |
| One-click installer | `install.sh` |
| CI workflow | `.github/workflows/ci.yml` |

---

## How to Start a New Session

1. Paste this document as first message (or reference it)
2. Read specific files if needed:
   ```
   read /Users/jason/Documents/Project/JobRadar/src/jobradar/interfaces/skill.py
   read /Users/jason/Documents/Project/JobRadar/src/jobradar/pipeline.py
   ```
3. Run a quick sanity check:
   ```bash
   cd /Users/jason/Documents/Project/JobRadar
   .venv/bin/jobradar health
   ```
4. Check CI is still green: https://github.com/jason-huanghao/jobradar/actions
