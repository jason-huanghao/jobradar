# JobRadar — OpenClaw Skill

JobRadar is an AI-powered job search agent that fetches, scores, and ranks job listings from multiple sources (Arbeitsagentur, Indeed, Google Jobs, BOSS直聘, 拉勾, 智联) against your CV, then generates tailored CVs and cover letters for top matches.

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

## Prerequisites

1. Install JobRadar:
   ```bash
   pip install -e ".[all]"
   ```

2. Configure LLM and CV path:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml
   ```

3. Set your LLM API key:
   ```bash
   export ARK_API_KEY=your_key_here   # Volcengine Ark
   # or: export OPENAI_API_KEY=...
   # or: export ZAI_API_KEY=...
   ```

4. Verify setup:
   ```bash
   jobradar status
   ```

---

## Available Tools

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

**Example invocation:**
> "Tell me more about that AI Engineer role at Siemens"

---

### `generate_application`
Generate an optimized CV + cover letter for a specific job.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_id` | string | ✓ | Job ID from `list_jobs` |

**Example invocation:**
> "Generate a cover letter for the top match"
> "Create application materials for job abc123"

**Returns:** `{ cv_optimized_md, cover_letter_md, gaps, application_id }`

---

### `get_digest`
Return a Markdown digest of the top-scoring jobs (good for a daily summary).

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
- Status tracking (new → interested → applied → interview)
- Excel export and Markdown digest

---

## CLI Commands

```bash
jobradar update               # Run full pipeline (daily cron job)
jobradar update --mode quick  # Quick run (fewer queries)
jobradar web                  # Start dashboard
jobradar status               # DB stats
jobradar setup                # Interactive setup wizard
```

### launchd daily agent (macOS)

```bash
jobradar install-agent        # Creates ~/Library/LaunchAgents/com.jobradar.update.plist
```

---

## Configuration Reference

See `config.example.yaml` for all options. Key fields:

| Section | Key | Description |
|---------|-----|-------------|
| `llm.text.provider` | string | LLM provider |
| `llm.text.model` | string | Model name |
| `candidate.cv_path` | path | Your CV file |
| `search.locations` | list | Cities to search |
| `search.max_days_old` | int | Only fetch recent jobs |
| `search.exclude_keywords` | list | Pre-filter titles |
| `scoring.min_score_application` | float | Auto-generate above this score |
| `sources.*.enabled` | bool | Enable/disable each scraper |
| `server.port` | int | Dashboard port (default 7842) |

---

## Troubleshooting

**No jobs returned:**
- Check API keys in `.env`
- Lower `max_days_old` or expand `locations`
- Run `jobradar update --mode dry-run` to test query generation

**LLM errors:**
- Check `data/cache/` for cached profile
- Test LLM: `jobradar health`

**BOSS直聘 / 拉勾 not working:**
- Cookie auth required — see adapter docstrings
- Set `BOSSZHIPIN_COOKIES` env var or place cookies in `memory/`

**Port conflict:**
- Change `server.port` in `config.yaml`
