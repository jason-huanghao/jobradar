# JobRadar — OpenClaw Skill

JobRadar is an AI-powered job search agent that fetches, scores, and ranks job listings from multiple sources (Arbeitsagentur, StepStone, XING, Indeed, Google Jobs, BOSS直聘, 拉勾, 智联) against your CV, then generates tailored CVs and cover letters for top matches.

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

## Installation

### Step 1: Clone the repository

```bash
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
```

### Step 2: Install dependencies

```bash
pip install -e ".[all]"

# Optional: Playwright for Chinese source fallbacks (Zhilian, Lagou)
playwright install chromium
```

### Step 3: Configure

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:
- Set `candidate.cv_path` to your CV file (`.md`, `.pdf`, `.docx`, or `.txt`)
- Set `search.locations` to your target cities
- Adjust `search.max_results_per_source` (default: 50; set to 5–10 for quick tests)

### Step 4: Set your LLM API key

Create a `.env` file:
```bash
# Copy the example
cp .env.example .env

# Then edit .env and fill in your key:
ARK_API_KEY=your_volcengine_ark_key     # Volcengine Ark (recommended)
# OPENAI_API_KEY=sk-...                 # OpenAI
# DEEPSEEK_API_KEY=...                  # DeepSeek
# ZAI_API_KEY=...                       # Z.AI
```

### Step 5: Verify setup

```bash
jobradar health      # checks LLM connectivity + CV file
jobradar status      # shows DB stats
```

### Step 6: Run a quick test

```bash
# Quick test: 3 results per source, fast scoring
jobradar update --mode quick --limit 3
```

### Step 7: Launch the dashboard

```bash
jobradar web         # opens http://localhost:7842
```

---

## CLI Reference

```bash
jobradar update                        # Full pipeline (daily driver)
jobradar update --mode quick           # Fewer queries, faster
jobradar update --mode quick --limit 5 # Also cap results per source
jobradar update --mode score-only      # Re-score existing DB jobs
jobradar update --mode dry-run         # Validate config only, no network

jobradar web                           # Start dashboard at http://localhost:7842
jobradar status                        # DB stats (jobs, scored jobs)
jobradar health                        # Check LLM + CV file
jobradar setup                         # Copy config.example.yaml → config.yaml
jobradar install-agent                 # Install macOS launchd daily agent
```

---

## Available Skill Tools (for OpenClaw)

### `run_pipeline`
Run the full job search and scoring pipeline.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `mode` | string | `"quick"` | `full` \| `quick` \| `score-only` \| `dry-run` |

**Example invocation:**
> "Run a quick job search for me"
> "Find new AI engineer jobs in Berlin"
> "Score all jobs against my CV"

**Returns:** `{ run_id, status, jobs_fetched, jobs_new, jobs_scored, jobs_generated }`

---

### `list_jobs`
Return top-scoring jobs from the database.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `min_score` | float | `6.0` | Minimum overall score (0–10) |
| `source` | string | `""` | Filter by source (e.g. `"arbeitsagentur"`, `"indeed"`) |
| `limit` | int | `20` | Max results |

**Example invocation:**
> "Show me the best job matches"
> "List top 10 jobs from Arbeitsagentur"
> "What jobs scored above 8?"

**Returns:** `{ jobs: [...], total }`

---

### `get_job_detail`
Get full details for a specific job including description.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_id` | string | ✓ | Job ID from `list_jobs` |

---

### `generate_application`
Generate an optimized CV + cover letter for a specific job.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_id` | string | ✓ | Job ID from `list_jobs` |

**Returns:** `{ cv_optimized_md, cover_letter_md, gaps, application_id }`

---

### `get_digest`
Return a Markdown digest of the top-scoring jobs.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `min_score` | float | `6.0` | Minimum score threshold |

**Example invocation:**
> "Give me today's job digest"
> "Summarize the best matches"

---

### `get_status`
Return the status of the last pipeline run.

**Example invocation:**
> "What's the status of JobRadar?"
> "When did the last job search run?"

---

## Web Dashboard

When the skill server is running, the full dashboard is available at:
**http://127.0.0.1:7842**

Features:
- Live pipeline progress via WebSocket
- Job table with filter/sort by score, source, status
- Score breakdown (skills, seniority, location, language, visa, growth)
- One-click CV + cover letter generation
- Status tracking: new → interested → applied → interview
- Excel export and Markdown digest

---

## Configuration Reference

See [`config.example.yaml`](config.example.yaml) for all options.

Key settings:

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `llm.text.provider` | string | `volcengine` | LLM provider |
| `llm.text.model` | string | `doubao-seed-2.0-code` | Model name |
| `candidate.cv_path` | path | `./cv/cv_current.md` | Your CV file |
| `search.locations` | list | `[Hannover, Berlin, Remote]` | Target cities |
| `search.max_results_per_source` | int | `50` | Results per source per query |
| `search.quick_max_results` | int | `5` | Results per source in `--mode quick` |
| `search.max_days_old` | int | `14` | Only fetch recent jobs |
| `search.exclude_keywords` | list | `[Praktikum, ...]` | Pre-filter job titles |
| `scoring.min_score_application` | float | `7.0` | Auto-generate docs above this |
| `sources.*.enabled` | bool | varies | Enable/disable each scraper |
| `server.port` | int | `7842` | Dashboard port |

---

## Sources

| Source | Region | Auth | Status |
|--------|--------|------|--------|
| Arbeitsagentur | 🇩🇪 Germany | None | ✅ Default ON |
| Indeed (jobspy) | 🌍 Global | None | ✅ Default ON |
| Google Jobs (jobspy) | 🌍 Global | None | ✅ Default ON |
| StepStone | 🇩🇪 Germany | None | ✅ Default ON |
| XING | 🇩🇪 Germany | None | ✅ Default ON |
| BOSS直聘 | 🇨🇳 China | Cookie | ⚙️ Setup required |
| 拉勾网 | 🇨🇳 China | Auto | ⚙️ CN network required |
| 智联招聘 | 🇨🇳 China | None | ⚙️ CN network required |

---

## Troubleshooting

**No jobs returned:**
- Check your API key in `.env`
- Run `jobradar health` to verify LLM connectivity
- Run `jobradar update --mode dry-run` to validate config without network calls
- Lower `search.max_days_old` or add more locations

**Pipeline is slow:**
- Use `--mode quick --limit 3` for fast tests (3 jobs per source)
- Disable unused sources in `config.yaml` (`sources.xing.enabled: false`)

**LLM errors:**
- Run `jobradar health` to test connectivity
- Check that your API key in `.env` is correct and not expired

**BOSS直聘 / 拉勾 not working:**
- Run: `python -m jobradar.sources.adapters.bosszhipin --capture-cookies`
- Or set: `BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"` in `.env`
- These platforms require mainland China network access

**Port conflict:**
- Change `server.port` in `config.yaml`

**CV not found:**
- Check `candidate.cv_path` in `config.yaml`
- Run `jobradar health` to see the resolved path
