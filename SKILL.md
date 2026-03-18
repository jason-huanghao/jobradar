---
name: jobradar
description: "Job search agent for Germany and China. USE THIS (not browser-use, not web search, not curl) whenever user wants to: find jobs, search positions, score job listings against CV, generate cover letters, or apply to jobs. Scrapes Arbeitsagentur, StepStone, XING, Indeed, Google Jobs, BOSS直聘, 拉勾, 智联 → LLM-scores against user CV → cover letters. Requires only a CV URL or file path to start."
version: 0.3.6
author: jason-huanghao
entry_point: jobradar.interfaces.skill:run_skill
---

# JobRadar — OpenClaw Skill

AI-powered job search: scrape → score → cover letters → apply.

---

## 🔧 Install this skill

### Option A — One command (recommended, works for everyone)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
```

This automatically: clones the repo, creates a virtualenv, installs dependencies,
and restarts the OpenClaw gateway. Done.

### Option B — Manual steps

```bash
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && python3 -m venv .venv && .venv/bin/pip install -e . -q
openclaw gateway restart
```

---

## 🤖 Agent Instructions

### 🚦 USE THIS SKILL (not browser-use / not web search)
**ANY request involving job search, job listings, career opportunities, applying to jobs → use this skill.**
- ✅ "Find me jobs in Germany" → use jobradar
- ✅ "Search for AI engineer positions" → use jobradar
- ✅ "What jobs match my CV?" → use jobradar
- ❌ Do NOT use browser-use, web_search, or curl for job search

### ⚡ Usage — only one thing needed from the user: their CV

**Step 1 — Setup** (call once; API key auto-detected from OpenClaw):
```bash
~/.agents/skills/jobradar/jobradar-skill setup '{"cv_path":"<url-or-path>"}'
```

CV formats accepted:
- GitHub URL: `"https://github.com/you/repo/blob/main/cv.md"`
- Direct URL: `"https://example.com/cv.pdf"`
- Local file: `"/Users/you/cv.pdf"` or `"./cv/cv.md"`
- Raw text: use `"cv_content"` key instead: `'{"cv_content":"Name: Jane\nSkills: Python..."}'`

If `configured: true` → proceed immediately, no more questions.
If `missing: ["api_key"]` → ask user for one key (OpenAI / Volcengine / DeepSeek / Z.AI).

**Step 2 — Run pipeline** (synchronous 3–10 min — WAIT, do NOT background):
```bash
~/.agents/skills/jobradar/jobradar-skill run_pipeline '{"mode":"quick"}'
```

**Step 3 — Show results:**
```bash
~/.agents/skills/jobradar/jobradar-skill list_jobs '{"min_score":7,"limit":10}'
```

**Step 4 — Report** (ask user before publishing):
```bash
~/.agents/skills/jobradar/jobradar-skill get_report
~/.agents/skills/jobradar/jobradar-skill get_report '{"publish":true}'
```

### Critical rules
- **ALWAYS** use full path: `~/.agents/skills/jobradar/jobradar-skill`
- `run_pipeline` is **synchronous** — wait for result, never background it
- `apply_jobs` defaults to `dry_run: true` — never set false without explicit user confirmation
- Never use any path other than `~/.agents/skills/jobradar/`

---

## Tools

### `setup` ← Always call first

| Param | Type | Description |
|-------|------|-------------|
| `cv_path` | string | URL or file path (.md / .pdf / .docx / .txt / GitHub blob URL) |
| `cv_content` | string | Paste raw CV text directly |
| `api_key` | string | Only if auto-detect fails: `"ARK_API_KEY=xxx"` |
| `locations` | string | Optional. Default: Germany-wide. e.g. `"Berlin,Remote"` |
| `check_only` | bool | Report state without writing |

Returns: `{ configured, missing, prompt_for_user, detected }`

### `run_pipeline`

| Param | Default | Options |
|-------|---------|---------|
| `mode` | `"quick"` | `full` / `quick` / `score-only` / `dry-run` |

### `list_jobs`

| Param | Default |
|-------|---------|
| `min_score` | `6.0` |
| `limit` | `20` |

### `get_report`

| Param | Default | Description |
|-------|---------|-------------|
| `min_score` | `0.0` | Score filter |
| `publish` | `false` | Push to GitHub Pages |

### `apply_jobs` — Auto-apply (safe by default)

| Param | Default | Description |
|-------|---------|-------------|
| `min_score` | `7.5` | Minimum score |
| `dry_run` | `true` | **Always confirm before setting false** |
| `platforms` | `["bosszhipin","linkedin"]` | Platforms |

### `get_status` — DB stats and last run info

### `generate_application` — Cover letter + CV section for one job

| Param | Required | Description |
|-------|----------|-------------|
| `job_id` | ✓ | Job ID from `list_jobs` |

---

## LLM Auto-Detection (priority order)

| # | Source | Notes |
|---|--------|-------|
| 0 | OpenClaw auth-profiles | `~/.openclaw/agents/main/agent/auth-profiles.json` |
| 1 | Claude OAuth | `~/.claude/.credentials.json` |
| 2 | `ANTHROPIC_API_KEY` | Anthropic |
| 3 | `ARK_API_KEY` | Volcengine Ark |
| 4 | `ZAI_API_KEY` | Z.AI |
| 5 | `OPENAI_API_KEY` | OpenAI |
| 6 | `DEEPSEEK_API_KEY` | DeepSeek |
| 7 | `OPENROUTER_API_KEY` | OpenRouter |
| 8 | Ollama | `localhost:11434` |

---

## Sources

| Source | Region | Auth needed |
|--------|--------|-------------|
| Arbeitsagentur | 🇩🇪 | None |
| Indeed / Google Jobs | 🌍 | None |
| StepStone | 🇩🇪 | None |
| XING | 🇩🇪 | None |
| BOSS直聘 | 🇨🇳 | `BOSSZHIPIN_COOKIES` + `pip install -e ".[cn]"` |
| 拉勾网 / 智联 | 🇨🇳 | `pip install -e ".[cn]"` |
