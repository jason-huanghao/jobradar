# JobRadar — Product Improvement Roadmap

*PM + Engineering perspective · Version 1.0 · March 2026*

---

## Executive Summary

JobRadar is a solid technical foundation but has friction at every onboarding step. This document proposes improvements across four themes: **zero-friction onboarding**, **richer CV input**, **deeper agent/skill integration**, and **feedback-loop intelligence**. Each item is rated by Impact × Effort.

---

## Theme 1 — Zero-Friction Onboarding

### 1.1 `--cv` flag + URL CV input ✅ *[IMPLEMENTED]*

**Problem:** Users had to copy their CV to a specific path before they could start.  
**Solution:** Any command now accepts `--cv <path-or-url>` to override the configured CV source.

```bash
# These all work now:
jobradar --cv ./my_cv.pdf
jobradar --cv https://mysite.com/cv.pdf
jobradar --cv https://raw.githubusercontent.com/me/repo/main/resume.md
jobradar --cv https://notion.so/your-exported-resume-page
```

**Supported URL formats:** HTML, PDF, Markdown, plain text, DOCX.  
**Implementation:** `src/cv_reader.py` — `read_cv_from_url()` detects format from `Content-Type` header + file extension, with html2text/BeautifulSoup/regex fallback chain.

---

### 1.2 `jobradar init` — True One-Command Bootstrap *(High Impact / Medium Effort)*

**Problem:** Current `--setup` wizard is interactive but still requires editing YAML manually.  
**Proposal:** A non-interactive `init` sub-command for CI/agent environments:

```bash
jobradar init \
  --cv https://mysite.com/cv.pdf \
  --locations "Berlin,Hamburg,Remote" \
  --llm openai \
  --key $OPENAI_API_KEY
# → Writes config.yaml, verifies LLM, runs --mode dry-run, prints summary
```

For OpenClaw skill invocation, an agent can call `jobradar init` with parameters extracted from conversation context — no human wizard interaction needed.

---

### 1.3 `--status` command *(High Impact / Low Effort)*

**Problem:** Users have no visibility into the pool state without opening Excel.  
**Proposal:**

```bash
jobradar --status
# Output:
# 📊 Job Pool: 312 total | 298 scored | 14 unscored
# ⭐ Top score: 8.4 — Senior ML Engineer @ DeepL (2 days ago)
# 📅 Last crawl: 2026-03-09 08:00 | Next: 2026-03-10 08:00
# 🗂️  Sources: BA ✅ Indeed ✅ Glassdoor ✅ BOSS直聘 ⚠️ (no cookies)
# 📬 Applied: 3 jobs this week
```

This is the first thing an AI agent should call to understand the current state before deciding what action to take.

---

### 1.4 `--health` command *(Medium Impact / Low Effort)*

A lightweight connectivity and config check:

```bash
jobradar --health
# ✅ LLM: doubao-seed-2.0-code (Volcengine Ark) — latency 340ms
# ✅ Bundesagentur API — reachable
# ✅ Indeed (JobSpy) — reachable
# ⚠️ BOSS直聘 — cookies missing (set BOSSZHIPIN_COOKIES)
# ✅ 智联招聘 — reachable (CN IP recommended for better results)
# ✅ Config: config.yaml OK
# ✅ CV: cv/cv_current.md — 2,840 chars (last parsed 2026-03-09)
```

Agents can call `jobradar --health` before deciding whether to proceed with a full run.

---

## Theme 2 — Richer CV Input

### 2.1 LinkedIn Profile URL *(High Impact / Medium Effort)*

**Proposal:** Accept a LinkedIn public profile URL directly.

```bash
jobradar --cv https://linkedin.com/in/yourhandle
```

**Implementation:** A dedicated `_extract_linkedin_html()` parser in `cv_reader.py` that maps the public profile DOM structure to a structured text format (name, headline, experience, skills sections). Falls back to generic HTML extraction if the profile is not publicly visible.

**Note:** LinkedIn aggressively blocks scraping. Best approach: user exports their own LinkedIn PDF (`linkedin.com/in/you/overlay/contact-info/` → "Save as PDF") and provides that URL or path.

---

### 2.2 CV Auto-Refresh *(Medium Impact / Low Effort)*

When `cv_url` is set, compare a lightweight hash of the remote resource against the cached hash on every run. Only re-parse if changed. This makes the URL workflow as efficient as the local file workflow.

```yaml
candidate:
  cv_url: "https://raw.githubusercontent.com/me/resume/main/cv.md"
  # → Checked on each run; re-parsed only when content changes
```

---

### 2.3 Multi-CV Profiles *(Medium Impact / Medium Effort)*

Support multiple CV variants for different target roles:

```yaml
candidate:
  cv_profiles:
    - name: "ml_engineer"
      cv_path: "./cv/cv_ml.md"
      custom_keywords: ["Machine Learning Engineer", "MLOps"]
    - name: "pm"
      cv_path: "./cv/cv_pm.md"
      custom_keywords: ["AI Product Manager", "产品经理"]
```

```bash
jobradar --profile ml_engineer
jobradar --profile pm
```

---

## Theme 3 — Agent & OpenClaw Skill Integration

### 3.1 Structured JSON Output *(High Impact / Low Effort)*

**Problem:** Agent frameworks parse terminal output as free text — fragile.  
**Proposal:** Add `--json` flag to all output-producing commands:

```bash
jobradar --status --json
# → {"pool": {"total": 312, "scored": 298}, "top_job": {...}, "sources": {...}}

jobradar --show-digest --json
# → {"jobs": [{"company": "...", "score": 8.4, "url": "..."}]}
```

This is the critical piece for OpenClaw/Claude Code to consume results programmatically and feed them into further agent actions (e.g., "draft an email to AMD using the top-scored job data").

---

### 3.2 SKILL.md Trigger Expansion *(High Impact / Low Effort)*

Current triggers are command-focused. Expand to also handle **context-rich natural language**:

```yaml
# Current (narrow):
triggers:
  - "search for jobs"
  - "find AI jobs"

# Proposed (rich context):
triggers:
  - pattern: "I'm looking for work in {location}"
    action: "jobradar --update --locations {location}"
  - pattern: "show me {role} jobs"  
    action: "jobradar --update --keywords '{role}'"
  - pattern: "apply to {company}"
    action: "jobradar --generate-app '{company}' && jobradar --mark-applied '{company}'"
  - pattern: "what jobs match my CV at {company}"
    action: "jobradar --explain '{company}'"
```

---

### 3.3 `jobradar serve` — MCP Server Mode *(High Impact / High Effort)*

Expose JobRadar as an MCP (Model Context Protocol) server so any MCP-compatible agent (Claude Code, Cursor, OpenClaw) can call it as a tool without CLI parsing:

```python
# MCP tool definitions
tools = [
    Tool(name="search_jobs",      description="Crawl all sources + score new jobs"),
    Tool(name="get_top_jobs",     description="Return top N scored jobs as JSON"),
    Tool(name="get_job_status",   description="Pool stats + last run info"),
    Tool(name="generate_cover",   description="Generate cover letter for a company"),
    Tool(name="mark_applied",     description="Mark job as applied"),
    Tool(name="record_feedback",  description="Record job preference for future scoring"),
]
```

```bash
jobradar serve --port 3001    # MCP server
# → Claude Code can then call jobradar.search_jobs() directly as a tool
```

---

### 3.4 Webhook Push *(Medium Impact / Medium Effort)*

Instead of only SMTP email, support webhook push for agents:

```yaml
notifications:
  webhook:
    enabled: true
    url: "https://n8n.example.com/webhook/jobradar"
    # or: "https://hooks.slack.com/services/..."
    # or: "https://api.telegram.org/bot{token}/sendMessage"
    events: ["new_high_score", "daily_digest"]
```

This allows OpenClaw to be notified passively when new high-score jobs appear, without polling.

---

## Theme 4 — Scoring Intelligence

### 4.1 `--preview-score` Prompt Debug *(High Impact / Low Effort)*

The most-requested missing feature from the code review. Show the exact prompt + LLM response for a specific job:

```bash
jobradar --preview-score "Databricks"
# → Prints the scoring prompt sent to LLM, the raw JSON response,
#   and the final weighted score breakdown
# Useful for: tuning prompts, understanding unexpected scores
```

---

### 4.2 Custom Scoring Weights *(Medium Impact / Low Effort)*

Let users adjust dimension weights in `config.yaml`:

```yaml
scoring:
  dimension_weights:
    skills_match: 2.0       # Double weight — most important for you
    visa_friendly: 1.5      # Important for visa holders
    location_fit: 1.0
    seniority_fit: 1.0
    language_fit: 0.8
    growth_potential: 0.7
```

---

### 4.3 Negative Filters *(Medium Impact / Low Effort)*

Hard-exclude jobs matching certain criteria before scoring (saves LLM tokens):

```yaml
search:
  exclude_keywords: ["Praktikum", "internship", "Werkstudent"]
  exclude_companies: ["CompanyX"]  # e.g., former employer
  min_salary_eur: 60000           # filter by salary range when available
```

---

## Theme 5 — Infrastructure

### 5.1 Parallel Crawling *(High Impact / Medium Effort)*

Current crawling is sequential — 7 sources × N queries = long serial chain.  
Migrate to `asyncio.gather()` or `ThreadPoolExecutor` across sources.  
Expected speedup: 3-5× for full pipeline runs.

### 5.2 Rate-Limit Aware Queue *(Medium Impact / Medium Effort)*

Persistent per-source rate-limit tracking in `memory/` so that if a run is interrupted and restarted, it doesn't immediately re-hit rate limits.

### 5.3 Docker One-Liner *(Medium Impact / Low Effort)*

```bash
docker run -e ARK_API_KEY=$ARK_API_KEY \
  -v $(pwd)/cv:/app/cv \
  -v $(pwd)/outputs:/app/outputs \
  ghcr.io/jason-huanghao/jobradar --update
```

---

## Priority Matrix

| # | Feature | Impact | Effort | Recommended Sprint |
|---|---------|--------|--------|-------------------|
| 1.1 | `--cv` URL input | ⭐⭐⭐ | S | ✅ Done |
| 1.3 | `--status` command | ⭐⭐⭐ | S | Sprint 1 |
| 3.1 | `--json` output flag | ⭐⭐⭐ | S | Sprint 1 |
| 4.1 | `--preview-score` | ⭐⭐⭐ | S | Sprint 1 |
| 1.2 | `jobradar init` | ⭐⭐⭐ | M | Sprint 2 |
| 1.4 | `--health` command | ⭐⭐ | S | Sprint 1 |
| 3.2 | SKILL.md triggers | ⭐⭐⭐ | S | Sprint 1 |
| 4.3 | Negative filters | ⭐⭐ | S | Sprint 1 |
| 4.2 | Score weights | ⭐⭐ | S | Sprint 2 |
| 2.1 | LinkedIn URL | ⭐⭐ | M | Sprint 2 |
| 2.3 | Multi-CV profiles | ⭐⭐ | M | Sprint 2 |
| 5.1 | Parallel crawling | ⭐⭐⭐ | M | Sprint 2 |
| 3.3 | MCP server mode | ⭐⭐⭐ | L | Sprint 3 |
| 3.4 | Webhook push | ⭐⭐ | M | Sprint 3 |
| 5.3 | Docker one-liner | ⭐⭐ | S | Sprint 2 |

*S = Small (1-2 days) · M = Medium (3-5 days) · L = Large (1-2 weeks)*
