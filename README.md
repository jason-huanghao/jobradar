<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603182230148.png" width="140" alt="JobRadar Logo" />

# JobRadar

### Stop applying blindly. Let AI find the right jobs for you.

[![GitHub Stars](https://img.shields.io/github/stars/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/network)
[![GitHub Issues](https://img.shields.io/github/issues/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/issues)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*An [OpenClaw](https://openclaw.ai) skill — runs standalone or inside any AI agent*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** reads your CV, searches **7 job platforms** across Germany and China in parallel, uses an LLM to score each role on 6 dimensions, generates tailored cover letters and CV sections, and can **auto-apply** to top matches on BOSS直聘 and LinkedIn — fully automated. Multi-user by design: each user's CV, scores, and LLM settings are scoped to their own profile.

---

<div align="center">

| 💬 Community & Feedback | ☕ Support This Project |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Public Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| Follow on WeChat for updates · send feedback directly | WeChat Pay · Alipay — no pressure, stars count too ⭐ |

</div>

---

## ⚡ Zero-Config with OpenClaw — 1 Message. Done.

If you use [OpenClaw](https://openclaw.ai), install the skill with **one command** and just share your CV:

**Step 1 — Install** (paste this into your terminal or tell OpenClaw to run it):
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
```
This clones, creates a virtualenv, installs deps, and restarts the OpenClaw gateway automatically.

**Step 2 — Use** (say this to OpenClaw or Claude):
```
Find me jobs in Germany. My CV: https://github.com/you/repo/blob/main/cv.md
```

The agent runs `setup` → scrapes 36+ jobs → scores with AI → publishes HTML report — **in one message, zero config files**.

> 📄 Live example: [report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---

## 📋 Navigation

| [✨ Features](#-features) | [⚙️ How It Works](#️-how-it-works) | [🚀 Quick Start](#-quick-start) |
|:---:|:---:|:---:|
| [🤖 OpenClaw & Claude](#-using-with-openclaw--claude) | [🔌 Job Sources](#-job-sources) | [🔌 LLM Providers](#-llm-providers) |
| [⚙️ Configuration](#️-configuration) | [🖥️ CLI Reference](#️-cli-reference) | [📊 Scoring System](#-scoring-system) |
| [🗂️ Project Structure](#️-project-structure) | [🤖 Auto-Apply](#-auto-apply) | [🗺️ Roadmap](#️-roadmap) |

---

## ✨ Features

| Feature | What you get |
|---------|-------------|
| 🌐 **7 job sources, parallel** | Arbeitsagentur, Indeed, Glassdoor, Google Jobs, StepStone, XING, BOSS直聘, 拉勾网, 智联招聘 — all at once |
| 🤖 **AI match scoring** | 6-dimension fit score (0–10) with full reasoning — know *why* a job ranked high |
| 🔑 **Zero-config API key** | Auto-detected from OpenClaw auth, Claude OAuth, or env vars |
| 🔌 **Any LLM, zero lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama — auto-detected |
| ✉️ **Tailored cover letters** | Company-specific, CV-aware, LLM-generated — not templates |
| 📝 **CV section optimizer** | Rewrites your summary + skills section to match each job description |
| 📊 **HTML report + Excel** | Shareable GitHub Pages report + colour-coded Excel tracker |
| 📰 **Markdown digest** | Top-matches summary via API or web dashboard |
| 🚀 **Auto-apply** | BOSS直聘 Playwright greet + LinkedIn Easy Apply (requires `[apply]` extra) |
| 🌐 **Web dashboard** | FastAPI UI — browse jobs, generate applications, download Excel |
| ⚡ **Incremental by design** | Only scores new jobs — daily updates finish in minutes |
| 🧠 **Learns from your feedback** | `jobradar apply --dry-run` previews; scoring adapts to your profile |
| 👥 **Multi-user** | Identity by `user.email`; CV is a versioned profile, scores keyed per profile — pass `--user` to scope any command |
| ⏳ **Expiry & freshness** | Tracks deadlines + posting age; `jobradar sweep` hides stale/expired jobs from reports & apply |
| 📡 **Source health signals** | `jobradar sources` shows per-source kind, status (ok/empty/error/blocked) and recent reliability; fetches retry on transient failure |
| ⚙️ **Per-user LLM settings** | `jobradar settings` shows/tests the effective endpoint; per-user override stored in DB (key name only, never the secret) |

---

## ⚙️ How It Works

```
Your CV (Markdown / PDF / DOCX / URL)
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ 1  DISCOVER  LLM parses CV → extracts target roles, │
│              skills, preferences, locations         │
│              Builds platform-specific search queries│
├─────────────────────────────────────────────────────┤
│ 2  CRAWL     7 sources run in parallel threads      │
│              Arbeitsagentur · Indeed · Glassdoor    │
│              Google Jobs · StepStone · XING  (DE)  │
│              BOSS直聘 · 拉勾网 · 智联招聘  (CN)     │
├─────────────────────────────────────────────────────┤
│ 0  SWEEP     Flag stale / past-deadline jobs as     │
│              expired (hidden from reports & apply)   │
├─────────────────────────────────────────────────────┤
│ 3  FILTER    Dedup by URL · Drop internships/noise  │
│              (free pre-filter — saves LLM tokens)   │
├─────────────────────────────────────────────────────┤
│ 4  SCORE     LLM rates each job on 6 axes (0–10):  │
│              Skills · Seniority · Location          │
│              Language · Visa · Growth potential     │
├─────────────────────────────────────────────────────┤
│ 5  GENERATE  ✉️  Cover letter per top match         │
│              📝 Tailored CV section per top match   │
├─────────────────────────────────────────────────────┤
│ 6  DELIVER   📊 HTML report (GitHub Pages)          │
│              📰 Markdown digest                     │
│              📁 Excel export (colour-coded)         │
│              🌐 Web dashboard                       │
│              🚀 Auto-apply (BOSS直聘 / LinkedIn)    │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

**Requirements:** Python 3.11+, one LLM API key, your CV.

### Fastest install (one command)
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
```
Detects your environment, clones the repo, creates a virtualenv, installs deps.

### Manual install
```bash
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e .                    # core (DE sources, no Playwright)
# pip install -e ".[cn]"           # add CN sources (Boss直聘, Lagou, Zhilian)
# pip install -e ".[apply]"        # add auto-apply (Boss直聘 greet + LinkedIn)
# pip install -e ".[web]"          # add web dashboard extras
```

### Provide your CV (pick any format)
```bash
# URL (GitHub, direct link, any HTTPS)
jobradar init --cv https://github.com/you/repo/blob/main/cv.md

# Local file — Markdown, PDF, DOCX, or plain text
jobradar init --cv /path/to/cv.pdf
jobradar init --cv ./cv/cv_current.md

# Interactive wizard (includes a paste-text option)
jobradar init
```

### First run
```bash
export OPENAI_API_KEY=sk-…          # or ARK_API_KEY, DEEPSEEK_API_KEY, etc.
jobradar init --email you@example.com  # identity — owns your profile & settings
jobradar health                     # verify LLM + CV
jobradar update --mode quick        # ~3 min fast test  (alias: jobradar run)
jobradar update                     # full run (all sources)
jobradar install-agent              # daily 08:00 automation (macOS)
```

> **Identity:** every command resolves a user from `--user`, then `user.email` in
> `config.yaml`. Your CV becomes a versioned **profile** under that user, and scores
> are keyed per profile — so multiple people can share one install without blending
> results. With a single user, set it once in `init` and omit `--user` thereafter.

---

## 🤖 Using with OpenClaw & Claude

### Option A — OpenClaw (Recommended)

Install skill once — API key auto-detected, **only your CV needed**.

**Daily workflow:**

| You say | What runs |
|---------|-----------|
| "Find me jobs. My CV: https://…" | `setup` → `run_pipeline` → `list_jobs` |
| "Publish my job report" | `get_report({publish:true})` → GitHub Pages URL |
| "Auto-apply to top matches" | `apply_jobs({dry_run:true})` → review then confirm |
| "Generate a cover letter for SAP" | `generate_application({job_id:"…"})` |

### Option B — Claude Code

Open the project directory. Claude Code reads `CLAUDE.md` automatically.

```bash
jobradar init --cv ./cv.md --api-key ARK_API_KEY=xxx
jobradar health && jobradar run --mode quick
```

### Option C — claude.ai + Desktop Commander MCP

With Desktop Commander connected, Claude can run all `jobradar` commands from your terminal.

---

## 🔌 Job Sources

All 7 sources are **fully implemented and active by default** (DE sources need no auth or Playwright):

### 🇩🇪 Europe — Germany

| Source | Auth required | Notes |
|--------|--------------|-------|
| **Bundesagentur für Arbeit** | None | Official German federal jobs API |
| **Indeed DE** | None | Via python-jobspy |
| **Glassdoor DE** | None | Via python-jobspy |
| **Google Jobs** | None | Via python-jobspy |
| **StepStone** | None | httpx + BeautifulSoup scraper |
| **XING** | None | httpx + BeautifulSoup scraper |

### 🇨🇳 China — requires `pip install -e ".[cn]"` + Playwright

| Source | Auth required | Notes |
|--------|--------------|-------|
| **BOSS直聘** | Browser cookie | `BOSSZHIPIN_COOKIES` env var — capture with `--capture-cookies` |
| **拉勾网** | None | 3-strategy cascade: mobile API → AJAX → Playwright |
| **智联招聘** | None | REST API → Playwright fallback |

**BOSS直聘 one-time setup (~2 min):**
```bash
python -m jobradar.sources.adapters.bosszhipin --capture-cookies
# Opens Chrome → log in → cookies auto-saved
```
Or manually: DevTools → Application → Cookies → copy `__zp_stoken__` + `wt2`:
```bash
export BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"
```

---

## 🔌 LLM Providers

Auto-detected in this priority order — **no config change needed** if your key is set:

| Priority | Source | Env var | Notes |
|----------|--------|---------|-------|
| 0 | **OpenClaw auth-profiles** | auto | Volcengine key from `~/.openclaw/…/auth-profiles.json` |
| 1 | **Claude OAuth** | auto | `~/.claude/.credentials.json` |
| 2 | `config.yaml` explicit | — | Pins a specific model |
| 3 | **Volcengine Ark** | `ARK_API_KEY` | doubao-seed series, best for CN |
| 4 | **Z.AI** | `ZAI_API_KEY` | Z.AI coding plan |
| 5 | **OpenAI** | `OPENAI_API_KEY` | gpt-4o-mini recommended |
| 6 | **DeepSeek** | `DEEPSEEK_API_KEY` | Most affordable |
| 7 | **OpenRouter** | `OPENROUTER_API_KEY` | 200+ models, one key |
| 8 | **Ollama** | *(none)* | Fully local, auto-detected |
| 9 | **LM Studio** | *(none)* | Local, auto-detected |

---

## ⚙️ Configuration

```bash
cp config.example.yaml config.yaml   # never commit this file
```

```yaml
user:
  email: you@example.com             # identity — owns your profile, scores & LLM settings

candidate:
  cv: "./cv/cv_current.md"           # .md, .pdf, .docx, or URL

search:
  locations: ["Berlin", "Hamburg", "Remote"]
  max_days_old: 14                   # posting TTL — older postings count as expired
  staleness_days: 7                  # not seen in N days → expired (sweep hides it)
  enrich_descriptions: true          # fetch detail pages to fill missing JD text
  enrich_max: 40                     # cap detail fetches per run (they are slow)
  exclude_keywords: ["Praktikum", "Werkstudent", "internship"]
  exclude_companies: ["MyFormerEmployer"]

reliability:
  max_attempts: 2                    # total tries per source on transient failure
  retry_base_delay: 0.5              # seconds; backoff = base * 2**(attempt-1)

scoring:
  min_score_digest: 6.0              # digest threshold
  min_score_application: 7.0         # cover letter + CV section generated
  auto_apply_min_score: 7.5          # threshold for jobradar apply
  max_desc_chars: 2000               # per-job description budget sent to the LLM scorer

sources:
  bosszhipin: { enabled: false }     # set true after cookie setup + pip install -e ".[cn]"
  lagou:      { enabled: false }
  zhilian:    { enabled: false }

server:
  port: 7842
  db_path: ./jobradar.db             # relative to install dir
```

Full annotated reference: [`config.example.yaml`](config.example.yaml)

---

## 🖥️ CLI Reference

Every command that reads or writes per-user data accepts `--user EMAIL`. Omit it to
fall back to `user.email` in `config.yaml`.

```bash
# ── Setup ─────────────────────────────────────────────────────────
jobradar init [--cv PATH_OR_URL] [--email YOU] [--api-key ENV=val] [--locations "X,Y"] [-y]
jobradar setup                     # non-interactive: copy config.example.yaml → config.yaml
jobradar health                    # LLM ping + CV file check
jobradar status                    # DB stats (job count, scored count)
jobradar install-agent             # macOS launchd: daily `update --mode quick` at 08:00

# ── Pipeline (run is an alias for update) ─────────────────────────
jobradar update                    # full run (sweep + fetch + score + generate)
jobradar update --mode quick       # fast test: fewer sources, ~3 min
jobradar update --mode dry-run     # validate config, no network calls
jobradar update --mode score-only  # skip fetching, re-score existing jobs
jobradar update --cv PATH_OR_URL   # override CV for this run
jobradar update --limit 5          # cap results per source (useful for testing)
jobradar update --user you@x.com   # scope to a specific user's profile

# ── Maintenance & introspection ───────────────────────────────────
jobradar sweep                     # flag stale / past-deadline jobs as expired
jobradar sources                   # per-source kind, enabled, recent reliability health
jobradar settings                  # show effective LLM endpoint (per-user override or config)
jobradar settings --test           # also ping the resolved endpoint

# ── Report ────────────────────────────────────────────────────────
jobradar report                    # generate HTML + open in browser
jobradar report --publish          # generate + push to GitHub Pages → prints URL
jobradar report --min-score 7      # only include jobs scored ≥ 7
jobradar report --no-open          # generate without opening browser

# ── Auto-apply ────────────────────────────────────────────────────
jobradar apply                     # interactive confirm each (safe default)
jobradar apply --dry-run           # preview — no actual submissions
jobradar apply --auto              # autonomous above score threshold
jobradar apply --min-score 8       # only best matches
jobradar apply --platforms bosszhipin,linkedin

# ── Web Dashboard ─────────────────────────────────────────────────
jobradar web                       # start at http://localhost:7842
jobradar web --port 8080           # custom port
jobradar web --no-browser          # don't auto-open
```

---

## 📊 Scoring System

Each job is scored 0–10 on six axes:

| Dimension | What it measures |
|-----------|-----------------|
| **Skills match** | Tech stack overlap — languages, frameworks, tools |
| **Seniority fit** | Your experience level vs. the role's expectation |
| **Location fit** | Commute viability, remote policy, relocation need |
| **Language fit** | DE/EN requirements vs. your actual proficiency |
| **Visa friendly** | Likelihood of work permit sponsorship |
| **Growth potential** | Domain relevance, company trajectory, learning |

Score ≥ `min_score_application` → cover letter + tailored CV section generated automatically.

---

## 🤖 Auto-Apply

JobRadar can automatically apply to top-scoring jobs using Playwright automation.

**Requirements:** `pip install -e ".[apply]" && playwright install chromium`

### BOSS直聘 (Boss直聘 greet)
- Opens job page, checks HR activity (skips if inactive > 7 days)
- Clicks 立即沟通 (Chat Now)
- Sends a customizable greeting message
- Random delay 3–8 s between applications, hard daily cap (default 50)
- **Requires:** `BOSSZHIPIN_COOKIES` env var

### LinkedIn Easy Apply
- Opens job page, clicks Easy Apply button
- Submits single-step applications (skips multi-step custom forms)
- Random delay 4–10 s, daily cap 25
- **Requires:** `LINKEDIN_COOKIES` env var (from browser DevTools)

```bash
jobradar apply --dry-run            # always preview first
jobradar apply --auto --min-score 8 # live apply, best matches only
```

---

## 🗂️ Project Structure

```
jobradar/
├── src/jobradar/
│   ├── sources/
│   │   ├── adapters/          # Job board scrapers (all 7 implemented)
│   │   │   ├── arbeitsagentur.py
│   │   │   ├── jobspy_adapter.py  # Indeed + Glassdoor + Google Jobs
│   │   │   ├── stepstone.py / xing.py
│   │   │   ├── bosszhipin.py      # cookie-based API + Playwright capture
│   │   │   ├── lagou.py / zhilian.py
│   │   ├── registry.py        # parallel fetch + retry + per-source outcomes
│   │   ├── health.py          # SourceOutcome / classify: ok·empty·error·blocked
│   │   └── report.py          # source × health join for `jobradar sources`
│   ├── scoring/
│   │   ├── scorer.py          # 6-dimension LLM scoring (batched)
│   │   ├── hard_filter.py     # free pre-filter (keywords, internships)
│   │   ├── freshness.py       # single source of truth for expiry date math
│   │   └── generator/         # cover_letter.py + cv_optimizer.py (per job)
│   ├── storage/               # SQLModel + Alembic (six-table schema)
│   │   ├── models.py          # User · Profile · Job · Score · Application · PipelineRun · UserSettings
│   │   ├── db.py              # engine + init_db (runs migrations to head)
│   │   └── repo.py            # user/profile resolution, list_scored, sweep_expired, settings
│   ├── llm/
│   │   ├── catalog.py         # curated provider catalog (single source of truth)
│   │   ├── resolver.py        # per-user endpoint override > config
│   │   ├── connection.py      # test_connection → ConnectionResult
│   │   ├── client.py          # OpenAI-compatible client
│   │   └── env_probe.py       # detect endpoint from env / OAuth / OpenClaw
│   ├── apply/                 # Auto-apply engine (Playwright): engine·boss·linkedin·history
│   ├── report/                # generator.py (HTML) + publisher.py (GitHub Pages)
│   ├── api/                   # FastAPI dashboard — routers/ + deps.py (per-user DI) + ws.py
│   ├── interfaces/
│   │   ├── cli.py             # Typer CLI (update/run/sweep/sources/settings/report/apply/…)
│   │   └── skill.py           # OpenClaw skill entry point
│   ├── pipeline.py            # JobRadarPipeline(config, user_email) orchestrator
│   └── config.py              # AppConfig — every field defaults; user.email required
├── migrations/                # Alembic: 0001_initial, 0002_user_settings
├── SKILL.md                   # OpenClaw skill manifest
├── jobradar-skill             # bash wrapper (auto-loads .env)
└── tests/                     # 83 passing — foundation·expiry·source_reliability·settings·cleanup·smoke
```

---

## 🗺️ Roadmap

- [x] Parallel source crawling (7 sources, ThreadPoolExecutor)
- [x] AI scoring (6 dimensions, batched LLM)
- [x] Cover letter generation + CV section optimizer
- [x] StepStone — full httpx + BeautifulSoup scraper
- [x] XING — full httpx + BeautifulSoup scraper
- [x] BOSS直聘 auto-apply (Playwright greet)
- [x] LinkedIn Easy Apply (Playwright)
- [x] HTML report + GitHub Pages publisher
- [x] Excel export (colour-coded, via web dashboard + API)
- [x] OpenClaw zero-config (API key from auth-profiles, no YAML needed)
- [x] Web dashboard (FastAPI, job browsing + application generation)
- [x] Multi-user model — `user.email` identity, versioned profiles, per-profile scores
- [x] Alembic migrations + clean six-table schema
- [x] Expiry & freshness — deadline/posting-age tracking + `jobradar sweep`
- [x] Source reliability — per-source health signals + retries (`jobradar sources`)
- [x] Per-user LLM settings + endpoint test (`jobradar settings`, `/api/settings`)
- [ ] Hardened Playwright browser crawler (deferred — instrument-first; see source health data)
- [ ] 前程无忧 (51job) CN source
- [ ] Daily digest push to Telegram / email
- [ ] MCP server mode (`jobradar serve`)
- [ ] Docker one-liner
- [ ] OpenClaw Cron integration (daily auto-run)

---

## 🤝 Contributing

Contributions welcome — especially source adapters and test coverage.

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ tests/ && pytest tests/ -v   # both gates are enforced in CI
```

> CI runs on Python 3.11 + 3.12. The `ruff check src/ tests/` lint gate is **blocking**
> (E501 line-length is globally ignored; ruff is pinned to `0.15.*` for reproducibility).
> The DB schema is managed by Alembic — `init_db()` upgrades to head, so a fresh
> checkout creates the six-table schema (+ `user_settings`, + `alembic_version`)
> with no manual steps.

---

## ⚠️ Disclaimer

For **personal job search, technical learning, and academic research only**.
Comply with each platform's `robots.txt` and Terms of Service.
No affiliation with any job platform listed.

---

## 📄 License

GNU General Public License v3.0 — see [LICENSE](LICENSE)

---

<div align="center">

Built for job hunters navigating Germany & China tech markets ❤️

**⭐ If JobRadar helped you land interviews, a star means a lot.**

</div>
