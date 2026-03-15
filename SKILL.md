# JobRadar — OpenClaw Skill

AI-powered job search agent: scrapes Arbeitsagentur, StepStone, XING, Indeed, Google Jobs,
BOSS直聘, 拉勾, 智联 → scores against your CV → generates cover letters for top matches.

---

## Skill Metadata

```yaml
skill_id: jobradar
display_name: JobRadar — AI Job Search
version: 0.2.0
author: jason-huanghao
entry_point: jobradar.interfaces.skill:run_skill
requires_server: true
server_port: 7842
```

---

## 🤖 Agent Instructions (for OpenClaw / AI assistants)

> **Goal: configure JobRadar in ≤2 user messages.**

### Minimal-turn flow

```
Step 1: call setup({})
        → returns: detected config + prompt_for_user string
        → show prompt_for_user to user (one message, not multiple questions)

Step 2: if configured=True → go to Step 4
        if missing=["cv"] → ask user once for CV (path / URL / paste)
        if missing=["api_key"] → ask user once for key
        if both missing → ask for both in one message

Step 3: call setup({...with what user provided...})
        → repeat until configured=True

Step 4: call run_pipeline({"mode": "quick"})
        → show results (top matches)
```

### Key behaviours

- **Auto-detects API keys** first — checks OPENCLAW_API_KEY, ARK_API_KEY, ZAI_API_KEY,
  OPENAI_API_KEY etc. **Never ask the user for a key before calling setup({}).**
- **Default locations** — Germany-wide (11 major cities + Remote).
  Only narrow if user explicitly requests specific cities.
- **GitHub CV URLs** — blob URLs auto-converted to raw. Pass them directly as cv_path.
- **prompt_for_user field** — always show this to the user verbatim; it contains the
  right question in the right tone.

### Ideal interaction (3 user messages)

```
User: set up JobRadar

Agent:  setup({})  →  "API key found (ARK_API_KEY). Just need your CV.
                        Path, URL, or paste text?"

User:   https://github.com/me/repo/blob/main/cv.md

Agent:  setup({"cv_path": "..."})  →  "✅ Ready! Run job search?"

User:   yes

Agent:  run_pipeline({"mode": "quick"})  →  shows top matches
```

---

## ⚡ Quick Install (one command)

Run this in a terminal — it clones, installs, and launches the setup wizard:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
```

The wizard will ask for:
1. Your LLM API key (auto-detects from environment if already set)
2. Your CV (file path, URL, or paste text directly)
3. Your target cities

---

## Manual Installation

```bash
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e ".[all]"
jobradar init        # interactive setup wizard
jobradar update --mode quick --limit 5   # quick test
```

---

## Skill Tools (for OpenClaw agents)

> **First time?** Call `setup` before any other tool.
> JobRadar auto-detects your OpenClaw/LLM API key — just provide your CV.

---

### `setup` ← **Start here**
Configure JobRadar (API key + CV + locations). Works without any pre-existing config.

**Parameters** (all optional — provide what you have):
| Name | Type | Description |
|------|------|-------------|
| `api_key` | string | `"ENV_VAR=value"` e.g. `"ARK_API_KEY=abc123"` or `"ZAI_API_KEY=xxx"` |
| `cv_path` | string | Local file path (`.md`, `.pdf`, `.docx`, `.txt`) or URL |
| `cv_content` | string | Raw CV text in Markdown (paste directly) |
| `locations` | string | Comma-separated e.g. `"Berlin,Hannover,Remote"` |
| `check_only` | bool | Just report current config status without changing anything |

**Auto-detection:** If `api_key` is omitted, JobRadar checks the environment for
`OPENCLAW_API_KEY`, `ARK_API_KEY`, `ZAI_API_KEY`, `OPENAI_API_KEY`, etc. automatically.

**Example calls:**
```json
// Minimal — let JobRadar auto-detect key, user provides CV path
setup({"cv_path": "/Users/jason/Documents/cv.pdf", "locations": "Berlin,Remote"})

// Provide everything explicitly
setup({
  "api_key": "ARK_API_KEY=your_key_here",
  "cv_path": "/Users/jason/cv.pdf",
  "locations": "Berlin,Hannover,Remote"
})

// Paste CV as text
setup({
  "cv_content": "# Jane Doe\nSoftware Engineer with Python, ML...",
  "locations": "Berlin,Remote"
})

// Just check current status
setup({"check_only": true})
```

**Returns:** `{ status, project_dir, api_key, cv, locations, configured, next_step }`

---

### `run_pipeline`
Fetch jobs from all sources, score against CV, generate cover letters for top matches.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `"quick"` | `full` \| `quick` \| `score-only` \| `dry-run` |

**Example invocations:**
> "Find new AI engineer jobs for me"
> "Run a quick job search"
> "Score all existing jobs against my CV"

**Returns:** `{ run_id, status, jobs_fetched, jobs_new, jobs_scored, jobs_generated }`

---

### `list_jobs`
Show top-scoring jobs from the database.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `min_score` | float | `6.0` | Minimum score 0–10 |
| `source` | string | `""` | Filter: `arbeitsagentur`, `stepstone`, `xing`, `jobspy:indeed` |
| `limit` | int | `20` | Max results |

> "Show me the best job matches"
> "What jobs scored above 8?"
> "List 5 jobs from StepStone"

**Returns:** `{ jobs: [{id, title, company, location, score, source, url, ...}], total }`

---

### `get_job_detail`
Full description + score breakdown for a specific job.

| Param | Required | Description |
|-------|----------|-------------|
| `job_id` | ✓ | Job ID from `list_jobs` |

---

### `generate_application`
Generate a tailored CV summary + cover letter for one job.

| Param | Required | Description |
|-------|----------|-------------|
| `job_id` | ✓ | Job ID from `list_jobs` |

> "Generate a cover letter for the Bosch AI role"

**Returns:** `{ cv_optimized_md, cover_letter_md, gaps }`

---

### `get_digest`
Markdown summary of top-scoring jobs (good for a daily briefing).

| Param | Type | Default |
|-------|------|---------|
| `min_score` | float | `6.0` |

> "Give me today's job digest"
> "Summarize the best matches"

---

### `get_status`
Status and stats of the last pipeline run.

> "When did JobRadar last run?"
> "How many jobs are in the database?"

---

## Recommended Agent Flow

```
1. setup({"check_only": true})                     → check if configured
2. setup({"cv_path": "...", "locations": "..."})   → configure if needed
3. run_pipeline({"mode": "quick"})                 → fetch + score jobs
4. list_jobs({"min_score": 7})                     → show top matches
5. generate_application({"job_id": "..."})         → create cover letter
6. get_digest({})                                  → daily summary
```

---

## CLI Reference (terminal)

```bash
jobradar init                            # Interactive setup wizard
jobradar update --mode quick --limit 5  # Fast test (cap per-source results)
jobradar update                          # Full daily pipeline
jobradar web                             # Dashboard at http://localhost:7842
jobradar status                          # DB stats
jobradar health                          # Check LLM + CV
jobradar install-agent                   # macOS launchd daily agent
```

---

## Configuration Reference

Key settings in `config.yaml` (auto-generated by `jobradar init`):

| Key | Default | Description |
|-----|---------|-------------|
| `candidate.cv_path` | `./cv/cv_current.md` | Your CV file |
| `search.locations` | `[Berlin, Remote]` | Target cities |
| `search.max_results_per_source` | `50` | Results per source (full mode) |
| `search.quick_max_results` | `5` | Results per source (quick mode) |
| `search.max_days_old` | `14` | Only recent jobs |
| `scoring.min_score_application` | `7.0` | Auto-generate docs above this |
| `server.port` | `7842` | Dashboard port |

---

## Sources

| Source | Region | Status |
|--------|--------|--------|
| Arbeitsagentur | 🇩🇪 | ✅ Default ON |
| Indeed / Google Jobs | 🌍 | ✅ Default ON |
| StepStone | 🇩🇪 | ✅ Default ON |
| XING | 🇩🇪 | ✅ Default ON |
| BOSS直聘 | 🇨🇳 | ⚙️ Cookie setup needed |
| 拉勾网 | 🇨🇳 | ⚙️ CN network required |
| 智联招聘 | 🇨🇳 | ⚙️ CN network required |

---

## Troubleshooting

**`needs_setup` response:**
→ Call `setup({})` — it will tell you exactly what's missing.

**No API key found:**
→ `setup({"api_key": "ARK_API_KEY=your_key"})` or `jobradar init`

**CV not found:**
→ `setup({"cv_path": "/path/to/cv.pdf"})` or paste: `setup({"cv_content": "# Name\n..."})`

**Pipeline is slow:**
→ `jobradar update --mode quick --limit 3`

**Port conflict:**
→ Set `server.port` in `config.yaml`

**BOSS直聘 / 拉勾 not working:**
→ These require mainland China network access
→ `python -m jobradar.sources.adapters.bosszhipin --capture-cookies`
