<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

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

> **JobRadar** reads your CV, searches 7 job platforms across Germany and China in parallel, uses an LLM to score each role on 6 dimensions against your profile, and delivers a daily digest + HTML report + tailored cover letters — fully automated. Drop your CV in, tell it where to look, let it run.

---

<div align="center">

| 💬 Community & Feedback | ☕ Support This Project |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Public Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| Follow on WeChat for updates · send feedback directly | WeChat Pay · Alipay — no pressure, stars count too ⭐ |

</div>

---

## ⚡ Zero-Config with OpenClaw — 1 Message. Done.

If you use [OpenClaw](https://openclaw.ai), JobRadar installs as a skill and **requires only your CV**. The API key is auto-detected from your OpenClaw environment — no YAML editing needed.

```bash
# One-time skill install
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && python3 -m venv .venv && .venv/bin/pip install -e . -q
openclaw gateway restart
```

Then just say:

```
Find me jobs in Germany. My CV: https://github.com/you/repo/blob/main/cv.md
```

The agent calls `setup` (API key auto-detected), scrapes 36+ jobs, scores with AI, and publishes an HTML report to GitHub Pages — **in two turns, zero config files touched**.

> 📄 Live example report: [report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---
## 📋 Navigation

| [✨ Features](#-features) | [⚙️ How It Works](#️-how-it-works) | [🚀 Quick Start](#-quick-start) |
|:---:|:---:|:---:|
| [🤖 OpenClaw & Claude](#-using-with-openclaw--claude) | [🔌 Job Sources](#-job-sources) | [🔌 LLM Providers](#-llm-providers) |
| [⚙️ Configuration](#️-configuration) | [🖥️ CLI Reference](#️-cli-reference) | [📊 Scoring System](#-scoring-system) |
| [🗂️ Project Structure](#️-project-structure) | [🗺️ Roadmap](#️-roadmap) | [🤝 Contributing](#-contributing) |

---

## ✨ Features

| Feature | What you get |
|---------|-------------|
| 🌐 **7 job sources, parallel** | Arbeitsagentur, Indeed, Glassdoor, Google Jobs, StepStone, BOSS直聘, 拉勾网, 智联招聘 — all at once |
| 🤖 **AI match scoring** | 6-dimension fit score (0–10) with full reasoning — know *why* a job ranked high |
| 🔑 **Zero-config API key** | Auto-detected from OpenClaw auth, Claude OAuth, or env vars — never type a key again |
| 🔌 **Any LLM, zero lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama — auto-detected |
| 📊 **HTML report + Excel** | Colour-coded tracker + shareable GitHub Pages report published in one command |
| 📰 **Daily digest** | Markdown top-matches summary pushed to your phone or inbox |
| ✉️ **Tailored cover letters** | Company-specific, CV-aware, LLM-generated — not templates |
| 📧 **Email push alerts** | SMTP digest with top new matches (Gmail App Password supported) |
| ⚡ **Incremental by design** | Only scores new jobs — daily updates finish in minutes, not hours |
| 🧠 **Learns your taste** | `--feedback "AMD liked"` — one command to bias all future scoring |
| 🤝 **Conversational + agent-ready** | Use from CLI, OpenClaw, Claude Code, or claude.ai — same commands |

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
│              Bundesagentur für Arbeit (DE)          │
│              Indeed · Glassdoor · Google Jobs       │
│              StepStone (DE)                         │
│              BOSS直聘 · 拉勾网 · 智联招聘 (CN)      │
├─────────────────────────────────────────────────────┤
│ 3  FILTER    Dedup by URL · Drop internships/noise  │
│              (free, before LLM — saves tokens)      │
├─────────────────────────────────────────────────────┤
│ 4  SCORE     LLM rates each job on 6 axes (0–10):  │
│              Skills · Seniority · Location          │
│              Language · Visa · Growth potential     │
├─────────────────────────────────────────────────────┤
│ 5  DELIVER   📊 HTML report (GitHub Pages)          │
│              📰 Daily Markdown digest               │
│              ✉️  Cover letter per top company       │
│              📧 Email push alert                    │
└─────────────────────────────────────────────────────┘
         ↑
         └── Feedback loop: your preferences
             refine future scoring automatically
```

---

## 🚀 Quick Start

**What you need:** Python 3.11+, one LLM API key, your CV.

```bash
# 1 — Clone & install
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — Set a key (any one provider works)
export OPENAI_API_KEY=sk-…          # OpenAI
# export DEEPSEEK_API_KEY=…         # DeepSeek (most affordable)
# export ARK_API_KEY=…              # Volcengine Ark (best for CN users)
# export ZAI_API_KEY=…              # Z.AI

# 3 — Bootstrap (writes config.yaml automatically)
jobradar --init --cv ./cv/cv_current.md --locations "Berlin,Hamburg,Remote"

# 4 — Verify everything is connected
jobradar --health

# 5 — First run
jobradar --mode quick               # ~3 min, 2 sources — good for testing
jobradar --update                   # full incremental run
jobradar --install-agent            # set up daily 8am automation
```

> 💡 **Dry-run first:** `jobradar --mode dry-run` shows all generated queries without hitting any APIs.

---
## 🤖 Using with OpenClaw & Claude

JobRadar is built to be operated conversationally — describe what you want, and the agent runs the right command.

### Option A — OpenClaw (Recommended)

Install the skill once, then chat naturally. **API key auto-detected from your OpenClaw profile** — the agent needs only your CV URL.

```bash
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && python3 -m venv .venv && .venv/bin/pip install -e . -q
openclaw gateway restart
```

**Daily workflow — what you say vs. what runs:**

| You say | What runs |
|---------|-----------|
| "Find me jobs. My CV: https://…" | `setup({cv_path})` → `run_pipeline` → `list_jobs` |
| "Is JobRadar ready?" | `jobradar --health --json` |
| "Show today's top matches" | `jobradar --show-digest --json` |
| "Write a cover letter for SAP" | `jobradar --generate-app "SAP"` |
| "I applied to Zalando" | `jobradar --mark-applied "Zalando"` |
| "Why did Databricks score low?" | `jobradar --explain "Databricks"` |
| "Publish my job report" | `get_report --publish` → GitHub Pages URL |
| "Set up daily automation" | `jobradar --install-agent` |

### Option B — Claude Code

Open the project directory. Claude Code reads `CLAUDE.md` automatically.

```bash
jobradar --init --cv ./cv.md --llm openai --key $OPENAI_API_KEY
jobradar --health && jobradar --mode quick
```

### Option C — Claude (claude.ai + MCP)

With Desktop Commander or Filesystem MCP connected, Claude can run all `jobradar` commands from your terminal.

---

## 🔌 Job Sources

### 🇩🇪 Europe — Germany focus

| Source | Platform | Status | Auth required |
|--------|----------|--------|---------------|
| **Bundesagentur für Arbeit** | Official German job board | ✅ Active | None |
| **Indeed DE** | Global job board | ✅ Active | None |
| **Glassdoor DE** | Jobs + company reviews | ✅ Active | None |
| **Google Jobs** | Aggregated global | ✅ Active | None |
| **StepStone** | DE premium job board | 🔧 Stub | — |
| **XING** | DACH professional network | 🔧 Stub | Apify token |

### 🇨🇳 China

| Source | Platform | Status | Auth required |
|--------|----------|--------|---------------|
| **BOSS直聘** | Top CN tech board | ✅ Active | Browser cookie + CN IP |
| **拉勾网** | Tech-focused | ✅ Active | Session cookie (auto-fetch) |
| **智联招聘** | Large general board | ✅ Active | None (CN IP recommended) |

> **CN platforms:** Best results from a Chinese IP. From Europe, use a VPN or run JobRadar on a CN cloud server.

**Enable CN sources:**
```yaml
search:
  locations: ["Berlin", "Remote", "上海", "北京"]
sources:
  zhilian:    { enabled: true }
  lagou:      { enabled: true }
  bosszhipin: { enabled: true }   # see BOSS直聘 cookie setup below
```

**BOSS直聘 one-time cookie setup (~2 min):**
1. Log in at [zhipin.com](https://www.zhipin.com) in Chrome
2. DevTools → Application → Cookies → `www.zhipin.com`
3. Copy `__zp_stoken__` and `wt2` values
4. `export BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"` in `.env`

---

## 🔌 LLM Providers

JobRadar auto-detects keys in this priority order — **no config change needed** if your key is already set.

| Priority | Source | Env var | Notes |
|----------|--------|---------|-------|
| 0 | **OpenClaw auth-profiles** | auto | Volcengine key from OpenClaw config |
| 1 | **Claude OAuth** | auto | `~/.claude/.credentials.json` |
| 2 | `config.yaml` explicit | — | Pins a specific model |
| 3 | **Volcengine Ark** | `ARK_API_KEY` | doubao-seed series, best for CN |
| 4 | **Z.AI** | `ZAI_API_KEY` | Z.AI coding plan |
| 5 | **OpenAI** | `OPENAI_API_KEY` | gpt-4o-mini recommended |
| 6 | **DeepSeek** | `DEEPSEEK_API_KEY` | Most affordable (~$0.14/1M tokens) |
| 7 | **OpenRouter** | `OPENROUTER_API_KEY` | 200+ models, one key |
| 8 | **Ollama** | *(none)* | Fully local, auto-detected |
| 9 | **LM Studio** | *(none)* | Local, auto-detected |

---
## ⚙️ Configuration

```bash
cp config.example.yaml config.yaml   # never commit this file
```

Key sections at a glance:
```yaml
candidate:
  cv: "./cv/cv_current.md"           # .md, .pdf, .docx, or cv_url: https://…

search:
  locations: ["Berlin", "Hamburg", "Remote"]
  max_days_old: 14
  exclude_keywords: ["Praktikum", "Werkstudent", "internship"]
  exclude_companies: ["MyFormerEmployer"]

scoring:
  min_score_digest: 6                # show in daily digest
  min_score_application: 7           # auto-generate cover letter
  auto_apply_min_score: 7.5          # threshold for apply_jobs tool

server:
  db_path: ./jobradar.db             # local to install dir — no ~/. leaks
  port: 7842
```

Full annotated reference: [`config.example.yaml`](config.example.yaml)

---

## 🖥️ CLI Reference

```bash
# ── First-time setup ──────────────────────────────────────────────
jobradar --init [--cv PATH_OR_URL] [--locations "X,Y"] [--llm PROVIDER] [--key KEY]
jobradar --setup                   # Interactive wizard
jobradar --install-agent           # Daily 8am automation (launchd/cron)
jobradar --uninstall-agent

# ── Inspect (agent-friendly) ──────────────────────────────────────
jobradar --health [--json]         # LLM + source connectivity check
jobradar --status [--json]         # Pool stats + source readiness

# ── Pipeline ──────────────────────────────────────────────────────
jobradar --update                  # Daily driver: new jobs only + email
jobradar --mode quick              # Fast test: Arbeitsagentur + Indeed, ~3 min
jobradar --mode dry-run            # Show queries, don't execute
jobradar --mode full               # Full pipeline, all sources
jobradar --crawl-only              # Fetch only, skip scoring
jobradar --score-only              # Score already-fetched jobs
jobradar --cv PATH_OR_URL          # Override CV for this run

# ── Conversational ────────────────────────────────────────────────
jobradar --show-digest [--json]    # Today's top jobs
jobradar --generate-app "Company"  # Cover letter
jobradar --mark-applied "Company"  # Mark as applied
jobradar --explain "Company"       # Full score breakdown
jobradar --feedback "AMD liked"    # Record preference for future runs
```

> `--json` on `--status`, `--health`, `--show-digest` → clean JSON on stdout, all banners → stderr.

---

## 📊 Scoring System

Each job is independently scored 0–10 on six axes:

| Dimension | What it measures |
|-----------|-----------------|
| **Skills match** | Tech stack overlap — languages, frameworks, tools |
| **Seniority fit** | Your years of experience vs. the role's expected level |
| **Location fit** | Commute viability, relocation need, remote-first policy |
| **Language fit** | DE/EN requirements vs. your actual proficiency |
| **Visa friendly** | Likelihood of work permit sponsorship |
| **Growth potential** | Domain relevance, company trajectory, learning opportunities |

Score ≥ `min_score_digest` → appears in daily digest
Score ≥ `min_score_application` → auto-generates a cover letter

---

## 🗂️ Project Structure

```
jobradar/
├── src/jobradar/
│   ├── sources/              # Job board adapters
│   │   ├── arbeitsagentur.py # Bundesagentur für Arbeit (DE)
│   │   ├── jobspy_adapter.py # Indeed + Glassdoor + Google
│   │   ├── bosszhipin.py     # BOSS直聘 (CN)
│   │   ├── lagou.py          # 拉勾网 (CN)
│   │   └── zhilian.py        # 智联招聘 (CN)
│   ├── report/
│   │   ├── generator.py      # Self-contained HTML report
│   │   └── publisher.py      # GitHub Pages deployment
│   ├── interfaces/
│   │   ├── skill.py          # OpenClaw skill entry point
│   │   └── cli.py            # CLI entry point
│   ├── config.py             # Config model (all paths relative)
│   ├── scorer.py             # LLM scoring engine (batched)
│   └── cv_parser.py          # CV → structured profile
├── SKILL.md                  # OpenClaw skill manifest
├── jobradar-skill            # Bash entry point (auto-loads .env)
├── config.example.yaml       # Annotated config template
└── tests/                    # 14/14 passing
```

---

## 🗺️ Roadmap

- [x] Parallel source crawling (ThreadPoolExecutor)
- [x] `--status` / `--health` / `--json` for agent consumption
- [x] `--init` non-interactive bootstrap
- [x] Negative keyword & company filters
- [x] CV from URL (PDF / HTML / Markdown / DOCX)
- [x] OpenClaw zero-config (API key from auth-profiles, no YAML needed)
- [x] Self-contained HTML report + GitHub Pages publisher
- [x] All paths relative to install dir (no `~/.jobradar` leaks)
- [ ] StepStone full implementation
- [ ] XING native adapter
- [ ] LinkedIn Easy Apply integration
- [ ] 前程无忧 (51job) CN source
- [ ] MCP server mode (`jobradar serve`)
- [ ] Docker one-liner
- [ ] Daily cron via OpenClaw (`openclaw cron add`)

---

## 🤝 Contributing

Contributions welcome — especially source adapters and test coverage.

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ && pytest tests/ -v
```

Priority areas: StepStone / XING / LinkedIn scrapers, `tests/` coverage, non-English README improvements.

---

## ⚠️ Disclaimer

This project is intended **for personal job search, technical learning, and academic research only**.

- Comply with each platform's `robots.txt` and Terms of Service
- Do not use for bulk commercial data collection or redistribution
- Users are solely responsible for any legal consequences
- No affiliation with any job platform listed

---

## 📄 License

GNU General Public License v3.0 — see [LICENSE](LICENSE)

---

<div align="center">

Built for job hunters navigating Germany & China tech markets ❤️

**⭐ If JobRadar helped you land interviews, a star means a lot.**

</div>
