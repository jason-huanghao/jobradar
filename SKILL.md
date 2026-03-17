# JobRadar — OpenClaw Skill

AI-powered job search agent: scrapes Arbeitsagentur, StepStone, XING, Indeed, Google Jobs,
BOSS直聘, 拉勾, 智联 → scores against your CV → generates cover letters for top matches.

---

## Skill Metadata

```yaml
skill_id: jobradar
display_name: JobRadar — AI Job Search
version: 0.3.0
author: jason-huanghao
entry_point: jobradar.interfaces.skill:run_skill
requires_server: true
server_port: 7842
```

---

## 🤖 Agent Instructions (for OpenClaw / AI assistants)

> **Goal: configure JobRadar in ≤2 user messages.**

### Minimal-turn setup flow

```
Step 1: call setup({})
        → auto-detects API key from environment
        → returns: detected config + prompt_for_user string
        → show prompt_for_user to user verbatim (one message only)

Step 2: if configured=True → skip to Step 4
        if missing=["cv"] → user provides CV (path / URL / paste text)
        if missing=["api_key"] → user provides key
        if both missing → ask for both in one message

Step 3: call setup({...with what user provided...})
        → repeat until configured=True

Step 4: call run_pipeline({"mode": "quick"})
        → show top matches to user
```

### Key behaviours

- **Auto-detects LLM keys first** — checks Claude OAuth, OPENCLAW_API_KEY, ARK_API_KEY,
  ZAI_API_KEY, OPENAI_API_KEY etc. **Never ask for a key before calling setup({}).**
- **CV accepts anything** — local path (.md/.pdf/.docx/.txt), GitHub URL, or pasted text.
  GitHub blob URLs are auto-converted to raw format.
- **Default locations** — worldwide (empty = no filter). Narrow only if user requests cities.
- **prompt_for_user field** — always show this verbatim; it contains the right question.

### Ideal interaction (3 user messages total)

```
User:   set up JobRadar

Agent:  setup({})
        → "API key found (OPENCLAW_API_KEY). Just need your CV.
           Path, URL, or paste your CV text?"

User:   https://github.com/jason-huanghao/daily-rss-digest/blob/main/cv_current.md

Agent:  setup({"cv_path": "https://github.com/.../cv_current.md"})
        → "✅ Ready! Run a quick job search now?"

User:   yes

Agent:  run_pipeline({"mode": "quick"})
        → shows top matches
```

---

## ⚡ Quick Install (one command)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
```

Or manually:

```bash
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e .          # core EU sources, no Playwright
pip install -e ".[all]"   # + CN sources + auto-apply (requires Playwright)
jobradar init             # interactive setup wizard
```

---

## Skill Tools

> **First time? Call `setup` before any other tool.**
> JobRadar auto-detects your API key — just provide your CV.

---

### `setup` ← Start here

Configure JobRadar (API key + CV + locations). Works without any pre-existing config.

**Parameters** (all optional):

| Name | Type | Description |
|------|------|-------------|
| `api_key` | string | `"ENV_VAR=value"` e.g. `"ARK_API_KEY=abc123"` |
| `cv_path` | string | File path or URL (.md / .pdf / .docx / .txt / GitHub URL) |
| `cv_content` | string | Raw CV text pasted directly as Markdown |
| `locations` | string | Comma-separated e.g. `"Berlin,Hamburg,Remote"` (default: worldwide) |
| `check_only` | bool | Report current config state without writing anything |

**Returns:** `{ status, configured, missing, detected, prompt_for_user }`

**Example calls:**

```json
// Check current state first
setup({"check_only": true})

// Provide CV via GitHub URL (blob URL auto-converted to raw)
setup({"cv_path": "https://github.com/me/repo/blob/main/cv.md"})

// Paste CV text directly
setup({"cv_content": "# Jane Doe\nSoftware Engineer, Python, ML..."})

// Provide everything at once
setup({"api_key": "ARK_API_KEY=xxx", "cv_path": "/Users/me/cv.pdf", "locations": "Berlin,Remote"})
```

---

### `run_pipeline`

Fetch + score + generate cover letters for top matches.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `"quick"` | `full` \| `quick` \| `score-only` \| `dry-run` |

**Returns:** `{ run_id, status, jobs_fetched, jobs_new, jobs_scored, jobs_generated }`

---

### `list_jobs`

Show top-scoring jobs from the database.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_score` | float | `6.0` | Minimum match score (0–10) |
| `source` | string | `""` | Filter by source: `arbeitsagentur`, `stepstone`, `xing`, `jobspy:indeed` |
| `limit` | int | `20` | Max results |

---

### `get_job_detail`

Full description + score breakdown for one job.

| Param | Required | Description |
|-------|----------|-------------|
| `job_id` | ✓ | Job ID from `list_jobs` |

---

### `generate_application`

Generate tailored CV summary + cover letter for one job.

| Param | Required | Description |
|-------|----------|-------------|
| `job_id` | ✓ | Job ID from `list_jobs` |

**Returns:** `{ cv_optimized_md, cover_letter_md, gaps }`

---

### `get_digest`

Markdown summary of top-scoring jobs (good for a daily briefing).

| Param | Type | Default |
|-------|------|---------|
| `min_score` | float | `6.0` |

---

### `get_report`

Generate a self-contained HTML report and optionally publish to GitHub Pages.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_score` | float | `0.0` | Only include jobs above this score |
| `publish` | bool | `false` | Push to GitHub Pages and return a public URL |

**Returns:** `{ report_path, job_count, url (if published), message }`

---

### `apply_jobs`

Apply to top-scoring jobs automatically. **Safe by default** — `dry_run=true` unless explicitly set false.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_score` | float | `7.5` | Minimum score to apply |
| `dry_run` | bool | `true` | Preview only — set `false` to actually submit |
| `platforms` | string/list | `["bosszhipin","linkedin"]` | Which platforms to apply on |
| `daily_limit` | int | `50` | Max applications this run |

**Requires cookies:** `BOSSZHIPIN_COOKIES` and/or `LINKEDIN_COOKIES` env vars.

**Returns:** `{ summary, applied, dry_run, results: [{job_id, title, company, status, message}] }`

---

### `get_status`

Status and stats of the last pipeline run and database.

---

## CLI Reference

```bash
jobradar run --cv <url_or_path>      # primary command — fetch + score
jobradar run --mode quick            # faster scan (fewer results per source)
jobradar run --mode full             # thorough daily run
jobradar run --mode dry-run          # validate config, no network calls

jobradar health                      # check LLM ping + CV file
jobradar status                      # DB stats (job count, scored count)
jobradar init                        # interactive setup wizard
jobradar web                         # start dashboard at http://localhost:7842
jobradar install-agent               # macOS launchd daily agent at 08:00
```

---

## Configuration

Minimal `config.yaml` — only CV is required, everything else defaults:

```yaml
candidate:
  cv: ""   # path, URL, or leave blank and use --cv flag
```

Full options (all have defaults, uncomment to override):

```yaml
# search:
#   locations: []          # empty = worldwide
#   max_results_per_source: 20
#   max_days_old: 14

# scoring:
#   min_score_digest: 6.0
#   min_score_application: 7.0
#   auto_apply_min_score: 7.5

# sources:
#   bosszhipin:
#     enabled: false       # needs: BOSSZHIPIN_COOKIES env var + pip install ".[all]"
#   lagou:
#     enabled: false       # needs: mainland China network
#   zhilian:
#     enabled: false

# server:
#   port: 7842
```

---

## LLM Provider Auto-Detection

JobRadar detects your LLM automatically in this priority order — no manual config needed:

| Priority | Source | Notes |
|----------|--------|-------|
| 0 | Claude OAuth | `~/.claude/.credentials.json` — free for Claude Code subscribers |
| 1 | `OPENCLAW_API_KEY` | OpenClaw runtime key via Z.AI proxy |
| 2 | `ZAI_API_KEY` | Z.AI direct |
| 3 | `ANTHROPIC_API_KEY` | Anthropic API |
| 4 | `ARK_API_KEY` | Volcengine Ark (doubao) |
| 5 | `OPENAI_API_KEY` | OpenAI |
| 6 | `DEEPSEEK_API_KEY` | DeepSeek |
| 7 | `OPENROUTER_API_KEY` | OpenRouter |
| 8 | Ollama local | `localhost:11434` |
| 9 | LM Studio local | `localhost:1234` |

---

## Sources

| Source | Region | Default | Notes |
|--------|--------|---------|-------|
| Arbeitsagentur | 🇩🇪 | ✅ ON | Federal Employment Agency REST API |
| Indeed / Google Jobs | 🌍 | ✅ ON | Via python-jobspy |
| StepStone | 🇩🇪 | ✅ ON | HTML scraper |
| XING | 🇩🇪 | ✅ ON | HTML scraper |
| BOSS直聘 | 🇨🇳 | ⚙️ OFF | Needs `BOSSZHIPIN_COOKIES` + `pip install ".[all]"` |
| 拉勾网 | 🇨🇳 | ⚙️ OFF | Needs mainland China network |
| 智联招聘 | 🇨🇳 | ⚙️ OFF | Needs mainland China network |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `needs_setup` response | Call `setup({})` — it tells you exactly what's missing |
| No API key found | `setup({"api_key": "ARK_API_KEY=xxx"})` or `jobradar init` |
| CV not found | `setup({"cv_path": "/path/to/cv.pdf"})` or paste via `cv_content` |
| Pipeline is slow | `jobradar run --mode quick --limit 3` |
| Port conflict | Set `server.port` in `config.yaml` |
| BOSS直聘 / 拉勾 not working | CN network required; run `python -m jobradar.sources.adapters.bosszhipin --capture-cookies` |
