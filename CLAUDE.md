# CLAUDE.md — Project Instructions for Claude Code

## What is this?
JobRadar: AI-powered job search agent for Germany-based AI/tech/PM/research roles.
Scrapes multiple job boards, scores matches with LLM, generates application materials.

## Architecture
```
config.yaml + cv/cv_current.md
    → CV Parser (LLM) → CandidateProfile
    → Query Builder → SearchQuery list
    → Sources (BA, JobSpy, StepStone, BOSS直聘)
    → Deduplicator → unique jobs
    → Scorer (LLM, batched) + feedback.json
    → Excel tracker + digest + cover letters + email
```

## Common Commands
```bash
jobradar --setup                  # interactive setup wizard
jobradar --mode quick             # fast test: BA + Indeed only
jobradar                          # full pipeline
jobradar --update                 # incremental (new jobs only) + email
jobradar --show-digest            # print today's digest
jobradar --generate-app "AMD"     # cover letter for AMD job
jobradar --mark-applied "SAP"     # mark as applied
jobradar --explain "Databricks"   # score breakdown
jobradar --feedback "AMD liked"   # record preference
jobradar --install-agent          # daily 8am automation
jobradar --rerun-scoring          # clear + re-score all
pytest tests/                      # run tests
```

## Key Design Decisions
- **LLM auto-detection** (`src/llm_env_probe.py`): At startup, `load_config()` probes the environment for a usable LLM key in priority order: (1) config.yaml explicit key, (2) agent framework env vars (OPENCLAW_API_KEY, ANTHROPIC_API_KEY, OPENCODE_API_KEY), (3) generic provider env vars (ZAI_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY, ARK_API_KEY, OPENROUTER_API_KEY), (4) local Ollama. If no key is found, `main.py` prints a setup guide and aborts. Commands that don’t require LLM (`--show-digest`, `--mark-applied`, `--feedback`) still work without a key.
- **LLM backend**: OpenAI-compatible client. Supports Volcengine Ark, Z.AI, DeepSeek, OpenAI, OpenRouter, Ollama — all via the same `base_url` + `api_key_env` pattern in `config.yaml`. No proxy needed.
- **CV format**: Markdown → CandidateProfile JSON via LLM. Schema: `schemas/candidate_profile.schema.json`
- **Job pool**: Persistent JSON at `memory/job_pool.json`. Keyed by normalized URL. Incremental — new runs only score truly new jobs.
- **Feedback loop**: `memory/feedback.json` is injected into the scorer prompt to bias future results.
- **Notifications**: SMTP email (Python smtplib, no extra deps). Gmail App Password recommended.
- **Empty fields**: Always `""` or `[]`, never `null`.

## Source Modules
| Module | Platform | Status |
|--------|----------|--------|
| `sources/arbeitsagentur.py` | Bundesagentur für Arbeit | ✅ P0 |
| `sources/jobspy_adapter.py` | Indeed + Google (python-jobspy) | ✅ P0 |
| `sources/stepstone_scraper.py` | StepStone DE | stub |
| `sources/xing_adapter.py` | XING | stub |
| `sources/bosszhipin.py` | BOSS直聘 | MVP |
| `sources/lagou.py` | 拉勾网 | planned |

## New Modules (Phase 1-3 additions)
| Module | Purpose |
|--------|---------|
| `setup_wizard.py` | `--setup` interactive wizard |
| `agent_installer.py` | `--install-agent` launchd/cron |
| `notifications/email_notifier.py` | SMTP email digest |
| `feedback.py` | `--feedback` preference learning |

## Config File Locations
Config is searched in this order:
1. `--config` CLI argument
2. `./config.yaml`
3. `<project_root>/config.yaml`
4. `~/.openclaw/jobradar/config.yaml`

## Testing
```bash
pytest tests/
pytest tests/test_scorer.py -v
pytest tests/test_cv_parser.py -v
```

## Data Paths
- `cv/cv_current.md` — Markdown CV (required)
- `cv/profile.md` — Optional free-form preferences
- `memory/` — Cache (gitignored): job_pool.json, candidate_profile.json, feedback.json
- `outputs/` — Generated (gitignored): Excel, digests, applications
