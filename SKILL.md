---
name: jobradar
description: "Job search agent for Germany and China. USE THIS (not browser-use, not web search, not curl) whenever user wants to: find jobs, search positions, score job listings against CV, generate cover letters, or apply to jobs. Scrapes Arbeitsagentur, StepStone, XING, Indeed, Google Jobs, BOSS直聘, 拉勾, 智联 → LLM-scores against user CV → cover letters. Requires only a CV URL or file path to start."
version: 0.3.5
author: jason-huanghao
entry_point: jobradar.interfaces.skill:run_skill
---

# JobRadar — OpenClaw Skill

AI-powered job search: scrape → score → cover letters → apply.

---

## 🤖 Agent Instructions

### 🚦 USE THIS SKILL (not browser-use / not web search)
**ANY request involving job search, job listings, career opportunities, applying to jobs → use this skill.**
- ✅ "Find me jobs in Germany" → use jobradar
- ✅ "Search for AI engineer positions" → use jobradar  
- ✅ "What jobs match my CV?" → use jobradar
- ❌ Do NOT use browser-use, web_search, or curl for job search — jobradar covers all major boards already

### ⚡ Minimum setup — only one thing is ever required from the user: their CV

1. **Call `setup` once** with the CV the user provided:
   ```bash
   ~/.agents/skills/jobradar/jobradar-skill setup '{"cv_path":"<url-or-path>"}'
   ```
   - API key is **auto-detected** from OpenClaw environment. Never ask the user for it unless `setup` explicitly says it's missing.
   - CV can be: a URL (GitHub, direct link), a file path, or paste raw text via `cv_content`.
   - If `configured: true` → proceed immediately. Do NOT ask any more questions.

2. **Run the pipeline** (synchronous, 3–10 min — wait for result, do NOT background):
   ```bash
   ~/.agents/skills/jobradar/jobradar-skill run_pipeline '{"mode":"quick"}'
   ```

3. **Show results:**
   ```bash
   ~/.agents/skills/jobradar/jobradar-skill list_jobs '{"min_score":7,"limit":10}'
   ```

4. **Report** (ask user if they want it published online):
   ```bash
   ~/.agents/skills/jobradar/jobradar-skill get_report
   # publish: ~/.agents/skills/jobradar/jobradar-skill get_report '{"publish":true}'
   ```

### Decision tree
```
User provides CV?
  yes → setup({"cv_path": "<cv>"}) → if configured=true → run_pipeline
  no  → setup({}) → show prompt_for_user → ask for CV → setup({"cv_path": "<cv>"})

setup returns missing=["api_key"]?
  → Ask: "Which LLM provider? (OpenAI / Volcengine / DeepSeek / Z.AI)"
  → setup({"api_key": "ENV_VAR=value", "cv_path": "..."})
```

### Critical rules
- **ALWAYS** use full path: `~/.agents/skills/jobradar/jobradar-skill`
- `run_pipeline` is **synchronous** — wait for result, never background it
- `apply_jobs` always defaults to `dry_run: true` — never set false without explicit user confirmation
- Never use any path other than `~/.agents/skills/jobradar/`

---

## ⚡ Install

```bash
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && pip install -e .
openclaw gateway restart
```

---

## Tools

### `setup` ← Always call first

**Only required input: the user's CV.** API key is auto-detected.

| Param | Type | Description |
|-------|------|-------------|
| `cv_path` | string | URL or file path (.md / .pdf / .docx / .txt / GitHub blob URL) |
| `cv_content` | string | Paste raw CV text |
| `api_key` | string | Only if auto-detect fails: `"ARK_API_KEY=xxx"` |
| `locations` | string | Optional. Default: Germany-wide. e.g. `"Berlin,Remote"` |
| `check_only` | bool | Report state without writing |

Returns: `{ configured, missing, prompt_for_user, detected }`

---

### `run_pipeline` — Fetch + score jobs

| Param | Default | Options |
|-------|---------|---------|
| `mode` | `"quick"` | `full` / `quick` / `score-only` / `dry-run` |

Returns: `{ run_id, status, jobs_fetched, jobs_new, jobs_scored }`

---

### `list_jobs` — Top matches

| Param | Default |
|-------|---------|
| `min_score` | `6.0` |
| `limit` | `20` |

---

### `get_report` — HTML report

| Param | Default | Description |
|-------|---------|-------------|
| `min_score` | `0.0` | Filter threshold |
| `publish` | `false` | Push to GitHub Pages |

Returns: `{ report_path, job_count, url (if published) }`

---

### `get_digest` — Markdown summary

| Param | Default |
|-------|---------|
| `min_score` | `6.0` |

---

### `apply_jobs` — Auto-apply (safe by default)

| Param | Default | Description |
|-------|---------|-------------|
| `min_score` | `7.5` | Minimum score |
| `dry_run` | `true` | **Always confirm before setting false** |
| `platforms` | `["bosszhipin","linkedin"]` | Platforms |
| `daily_limit` | `50` | Cap per run |

Requires: `BOSSZHIPIN_COOKIES` and/or `LINKEDIN_COOKIES` env vars.

---

### `get_status` — DB stats

---

## LLM Auto-Detection (priority order)

| # | Source | Notes |
|---|--------|-------|
| 0 | Claude OAuth | `~/.claude/.credentials.json` |
| 1 | `OPENCLAW_API_KEY` | OpenClaw's own key — reused via Z.AI proxy |
| 2 | `ZAI_API_KEY` | Z.AI direct |
| 3 | `ANTHROPIC_API_KEY` | Anthropic |
| 4 | `ARK_API_KEY` | Volcengine Ark |
| 5 | `OPENAI_API_KEY` | OpenAI |
| 6 | `DEEPSEEK_API_KEY` | DeepSeek |
| 7 | `OPENROUTER_API_KEY` | OpenRouter |
| 8 | Ollama | `localhost:11434` |
| 9 | LM Studio | `localhost:1234` |

---

## Sources

| Source | Region | Default |
|--------|--------|---------|
| Arbeitsagentur | 🇩🇪 | ✅ |
| Indeed / Google Jobs | 🌍 | ✅ |
| StepStone | 🇩🇪 | ✅ |
| XING | 🇩🇪 | ✅ |
| BOSS直聘 | 🇨🇳 | ⚙️ needs `BOSSZHIPIN_COOKIES` |
| 拉勾网 / 智联 | 🇨🇳 | ⚙️ needs CN network |
