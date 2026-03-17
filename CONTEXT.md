# JobRadar — Project Context for Continuation Sessions

> **Read this first in any new session.**

---

## Identity

| Field | Value |
|-------|-------|
| Package name | `openclaw-jobradar` v0.3.0 |
| Local path | `/Users/jason/Documents/Project/JobRadar` |
| GitHub | https://github.com/jason-huanghao/jobradar |
| Venv | `.venv/bin/python` (Python 3.11, all deps installed) |
| Run commands | `cd .../JobRadar && .venv/bin/jobradar ...` |
| LLM key | `ARK_API_KEY` in `.env` (Volcengine Ark, `doubao-seed-2.0-code`) |
| CV | `cv/cv_current.md` (Hao Huang, PhD candidate, AI/ML/KG) |
| DB | `jobradar.db` (SQLite, ~800+ jobs scraped) |
| Cache | `memory/` (profile JSON cached here) |
| Reports | `~/.jobradar/reports/` (HTML reports) |
| Apply history | `~/.jobradar/apply_history.json` |

---

## Sprint Status (as of v0.3.0)

| Sprint | Status | What shipped |
|--------|--------|-------------|
| 0 — Reconstruct | ✅ Done | config.py restored, env_probe.py written, --cv flag, cv: key, docs/ deleted, 9 tests |
| 1 — HTML Report | ✅ Done | `jobradar report`, `--publish` (GitHub Pages), DB auto-detect, `get_report` skill tool, 11 tests |
| 2 — Auto-apply | ✅ Done | apply engine (Boss直聘 + LinkedIn), `jobradar apply`, `apply_jobs` skill tool, 14 tests |
| 3 — OpenClaw E2E | ✅ Done | All 7 skill tools verified: setup→pipeline→list→report→apply→digest→status |
| 4 — GH Pages live | 🔲 Next | `jobradar report --publish` live test, enable Pages on repo |

---

## Verified End-to-End (Sprint 3 local simulation)

```
setup({})                    → configured=True, ARK_API_KEY detected
setup({"cv_path": "<url>"})  → CV downloaded, configured=True
run_pipeline({"mode":"quick"})→ fetched=63, scored=61, generated=1
list_jobs({"min_score":7})   → 5 jobs, top score 9.0 (Agentic AI Engineer @ GAIA AG)
get_report({})               → 801 jobs, report saved to ~/.jobradar/reports/
apply_jobs({"dry_run":true}) → 0 results (EU jobs have no Boss/LinkedIn URLs — expected)
get_digest({"min_score":8})  → Markdown digest of top 16 matches
get_status({})               → {status, last_run, jobs_scored}
```

---

## Architecture (v0.3.0)

```
src/jobradar/
├── config.py           AppConfig, defaults-first, cv: key, DB auto-detect
├── pipeline.py         7-step orchestrator
├── models/             RawJob, ScoredJob, CandidateProfile
├── profile/            CV ingestor + LLM extractor + file/URL readers
├── sources/            8 adapters (Arbeitsagentur, StepStone, XING, Indeed,
│                       Google, Boss直聘, Lagou, Zhilian)
├── scoring/            Hard filter + LLM scorer + CV/cover-letter generator
├── storage/            SQLite via SQLModel (~/.jobradar/jobradar.db default)
├── report/             ← NEW Sprint 1
│   ├── generator.py    Self-contained HTML report (_HTML_TEMPLATE, str.replace)
│   └── publisher.py    GitHub Pages via git worktree
├── apply/              ← NEW Sprint 2
│   ├── base.py         ApplyResult, ApplySession, Applier protocol
│   ├── history.py      ApplyHistory (~/.jobradar/apply_history.json)
│   ├── engine.py       run_apply() orchestrator
│   ├── boss.py         Boss直聘 Playwright auto-greet
│   └── linkedin.py     LinkedIn Easy Apply
├── api/                FastAPI skill server (port 7842)
├── interfaces/
│   ├── cli.py          run/update/report/apply/health/status/init/web
│   └── skill.py        run_skill() — 8 tools including get_report, apply_jobs
└── llm/
    ├── client.py       LLMClient (OpenAI-compatible)
    └── env_probe.py    detect_endpoint(): OAuth→OpenClaw→ARK→…→Ollama
```

---

## CLI Reference (v0.3.0)

```bash
jobradar run --cv <url_or_path>      # fetch + score (primary command)
jobradar run --mode quick            # fast scan
jobradar run --mode dry-run          # validate config only
jobradar report                      # generate HTML report, open browser
jobradar report --publish            # push to GitHub Pages, print URL
jobradar report --min-score 7        # only jobs >= 7
jobradar apply                       # interactive confirm each
jobradar apply --auto                # autonomous above 7.5
jobradar apply --auto --min-score 8  # only best matches
jobradar apply --dry-run             # preview without submitting
jobradar health                      # LLM ping + CV check
jobradar status                      # DB stats
jobradar init                        # interactive setup wizard
jobradar web                         # dashboard at http://localhost:7842
jobradar install-agent               # macOS launchd daily at 08:00
```

---

## Skill Tools (OpenClaw)

| Tool | Purpose |
|------|---------|
| `setup` | Configure: api_key, cv_path/cv_content, locations, check_only |
| `run_pipeline` | Fetch + score + generate (mode: quick/full/score-only/dry-run) |
| `list_jobs` | Top jobs by score (min_score, source, limit) |
| `get_job_detail` | Full description + score breakdown by job_id |
| `generate_application` | CV + cover letter for a job |
| `get_digest` | Markdown digest of top matches |
| `get_report` | HTML report (min_score, publish=true for GitHub Pages URL) |
| `apply_jobs` | Auto-apply (min_score, dry_run=true default, platforms, daily_limit) |
| `get_status` | Last pipeline run stats |

---

## LLM Provider Priority

```
0. Claude OAuth    ~/.claude/.credentials.json (free for Claude Code subscribers)
1. OPENCLAW_API_KEY → Z.AI proxy
2. ZAI_API_KEY     → Z.AI direct
3. ANTHROPIC_API_KEY
4. ARK_API_KEY     → Volcengine Ark (doubao)
5. OPENAI_API_KEY
6. DEEPSEEK_API_KEY
7. OPENROUTER_API_KEY
8. LM Studio local  (localhost:1234)
9. Ollama local     (localhost:11434)
```

---

## Config (minimal — only CV required)

```yaml
# config.yaml — only this line is required:
candidate:
  cv: ""   # path, URL, or use --cv flag on CLI

# Everything else defaults:
# search.locations: []          (worldwide)
# scoring.auto_apply_min_score: 7.5
# sources: all EU ON, all CN OFF (need cookies)
# server.port: 7842
```

---

## Known State / Next Tasks

- [ ] **Sprint 4**: `jobradar report --publish` live test — enable GitHub Pages on repo settings, then run and verify URL
- [ ] **Boss直聘 live apply**: Set `BOSSZHIPIN_COOKIES`, run `jobradar apply --dry-run`, then `--auto --min-score 8`
- [ ] **OpenClaw live test**: Reload SKILL.md from GitHub in OpenClaw, run conversation with cv_current.md URL
- [ ] **pytest CI**: Update `.github/workflows/ci.yml` to run `pytest tests/` instead of inline python -c tests
- [ ] **LinkedIn Easy Apply live**: Set `LINKEDIN_COOKIES`, test against real LinkedIn jobs

---

## Test Suite (14/14 green)

```
test_imports                  — all modules importable
test_config_defaults          — AppConfig defaults correct
test_config_cv_override       — --cv flag override works
test_normalizer_dedup         — URL-based dedup correct
test_hard_filter_drops_excluded — Praktikum/Werkstudent filtered
test_env_probe_no_keys        — returns None with no keys
test_skill_setup_check_only   — returns structured JSON
test_skill_setup_cv_content   — writes cv_current.md
test_report_generates_html    — valid HTML with embedded JSON
test_report_score_filter      — score data embedded correctly
test_query_builder_max_results — max_results propagated
test_apply_history            — dedup and daily count
test_apply_engine_dry_run     — DRY_RUN status returned
test_boss_helpers             — inactive HR detection + greeting format
```
