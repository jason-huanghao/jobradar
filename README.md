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

> **JobRadar** reads your CV, searches 7 job platforms across Germany and China in parallel, uses an LLM to score each role on 6 dimensions against your profile, and delivers a daily digest + Excel tracker + tailored cover letters — fully automated. Drop your CV in, tell it where to look, and let it run.

---

<div align="center">

| 💬 Community & Feedback | ☕ Support This Project |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101718363.png" width="160" alt="WeChat Public Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101748931.png" width="300" alt="WeChat Pay & Alipay" /> |
| Follow on WeChat for updates · send feedback directly | WeChat Pay · Alipay — no pressure, stars count too ⭐ |

</div>

---

## 📋 Navigation

| [✨ Features](#-features) | [⚙️ How It Works](#️-how-it-works) | [🚀 Quick Start](#-quick-start) |
|:---:|:---:|:---:|
| [🤖 With OpenClaw & Claude](#-using-with-openclaw--claude) | [🔌 Job Sources](#-job-sources) | [🔌 LLM Providers](#-llm-providers) |
| [⚙️ Configuration](#️-configuration) | [🖥️ CLI Reference](#️-cli-reference) | [📊 Scoring System](#-scoring-system) |
| [🗂️ Project Structure](#️-project-structure) | [🗺️ Roadmap](#️-roadmap) | [🤝 Contributing](#-contributing) |

---

## ✨ Features

| Feature | What you get |
|---------|-------------|
| 🌐 **7 job sources, parallel** | Bundesagentur, Indeed, Glassdoor, Google Jobs, StepStone, BOSS直聘, 拉勾网, 智联招聘 — all at once |
| 🤖 **AI match scoring** | 6-dimension fit score (0–10) with full reasoning — know *why* a job ranked high |
| 🔌 **Any LLM, zero lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama — auto-detected from env |
| 📊 **Excel tracker** | Colour-coded by score, applied status, date posted — one file, everything in it |
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
│ 5  DELIVER   📊 Excel tracker (colour-coded)        │
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

> 💡 **Already inside an AI agent?** Just say *"Set up JobRadar, my CV is at https://… and my OpenAI key is sk-…"* — OpenClaw or Claude Code will run the `--init` command for you. No YAML editing needed.

> 💡 **Dry-run first:** `jobradar --mode dry-run` shows all generated queries without hitting any APIs.

---

## 🤖 Using with OpenClaw & Claude

JobRadar is built to be operated conversationally — describe what you want, and the agent runs the right command.

### Option A — OpenClaw

Place the `jobradar/` folder in your OpenClaw skills directory. OpenClaw reads `SKILL.md` automatically.

**Zero-config onboarding — one message:**
```
You:  Set up JobRadar. My CV is at https://mysite.com/cv.pdf,
      I want AI/ML jobs in Berlin and Munich,
      and my OpenAI key is sk-xxxx
```
OpenClaw runs `jobradar --init --cv … --locations … --llm openai --key …`, writes `config.yaml` and `.env`, then confirms setup.

**Daily workflow:**

| You say | What runs |
|---------|-----------|
| "Check if JobRadar is ready" | `jobradar --health --json` |
| "What's in my job pool?" | `jobradar --status --json` |
| "Find me AI jobs now" | `jobradar --mode quick` |
| "Show me today's top matches" | `jobradar --show-digest --json` |
| "Write a cover letter for DeepL" | `jobradar --generate-app "DeepL"` |
| "I applied to Zalando" | `jobradar --mark-applied "Zalando"` |
| "Why did Databricks score low?" | `jobradar --explain "Databricks"` |
| "Set up daily automation" | `jobradar --install-agent` |

### Option B — Claude Code

Open the project directory. Claude Code reads `CLAUDE.md` automatically.
```bash
jobradar --init --cv ./cv.md --llm openai --key $OPENAI_API_KEY
jobradar --health && jobradar --mode quick
```
Or just ask: *"Set up JobRadar and find ML jobs in Munich"*

### Option C — Claude (claude.ai + MCP)

With Desktop Commander or Filesystem MCP connected, Claude can run all `jobradar` commands from your terminal.

### Minimum config (13 lines, auto-generated by `--init`)

```yaml
candidate:
  cv_url: "https://mysite.com/cv.pdf"   # or cv_path: "./cv/cv.md"
llm:
  text:
    provider: "openai"
    model: "gpt-4o-mini"
    api_key_env: "OPENAI_API_KEY"
search:
  locations: ["Berlin", "Hamburg", "Remote"]
sources:
  arbeitsagentur: { enabled: true }
  jobspy: { enabled: true, boards: ["indeed", "google"], country: "germany" }
```

> 📖 Full guide: [docs/GUIDE_OPENCLAW_CLAUDE.md](docs/GUIDE_OPENCLAW_CLAUDE.md)

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

> **CN platforms note:** Best results from a Chinese IP. From Europe, use a VPN or run JobRadar on a CN cloud server (Alibaba Cloud ECS, etc.).

**Enable CN sources** — add cities and flip the switches:
```yaml
search:
  locations: ["Berlin", "Remote", "上海", "北京"]
sources:
  zhilian:   { enabled: true }        # no auth needed
  lagou:     { enabled: true }        # auto-fetches cookies
  bosszhipin: { enabled: true }       # see cookie setup below
```

**BOSS直聘 one-time cookie setup (~2 min):**
1. Log in at [zhipin.com](https://www.zhipin.com) in Chrome
2. DevTools → Application → Cookies → `www.zhipin.com`
3. Copy `__zp_stoken__` and `wt2` values
4. `export BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"` in `.env`

---

## 🔌 LLM Providers

JobRadar auto-detects the first available key at startup — **no config change needed** if your key is already in the environment.

| Priority | Provider | Env var | Notes |
|----------|----------|---------|-------|
| 1 | `config.yaml` explicit | — | Pins a specific model |
| 2 | **Volcengine Ark** | `ARK_API_KEY` | doubao-seed series, best for CN |
| 3 | **Z.AI** | `ZAI_API_KEY` | Z.AI coding plan |
| 4 | **OpenAI** | `OPENAI_API_KEY` | gpt-4o-mini recommended |
| 5 | **DeepSeek** | `DEEPSEEK_API_KEY` | Most affordable (~$0.14/1M tokens) |
| 6 | **OpenRouter** | `OPENROUTER_API_KEY` | 200+ models, one key |
| 7 | **Ollama** | *(none)* | Fully local, auto-detected |

All providers use the OpenAI-compatible API format. Switch by changing `base_url` + `api_key_env` in config.

---

## ⚙️ Configuration

```bash
cp config.example.yaml config.yaml   # never commit this file
```

Key sections at a glance:
```yaml
candidate:
  cv_path: "./cv/cv_current.md"      # .md, .pdf, .docx, or cv_url: https://…

search:
  locations: ["Berlin", "Hamburg", "Remote"]
  max_days_old: 14
  exclude_keywords: ["Praktikum", "Werkstudent", "internship"]  # free filter
  exclude_companies: ["MyFormerEmployer"]                        # skip entirely

scoring:
  min_score_digest: 6                # show in daily digest
  min_score_application: 7           # auto-generate cover letter
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
jobradar --update                  # ★ Daily driver: new jobs only + email
jobradar                           # Full pipeline (crawl + score + output)
jobradar --mode quick              # Fast test: BA + Indeed, ~3 min
jobradar --mode dry-run            # Show queries, don't execute
jobradar --crawl-only / --score-only / --rerun-scoring / --parse-cv-only
jobradar --cv PATH_OR_URL          # Override CV for this run

# ── Conversational ────────────────────────────────────────────────
jobradar --show-digest [--json]    # Today's top jobs
jobradar --generate-app "Company"  # Cover letter
jobradar --mark-applied "Company"  # Mark as applied + update Excel
jobradar --explain "Company"       # Full score breakdown
jobradar --feedback "AMD liked"    # Record preference for future runs
```

> `--json` on `--status`, `--health`, `--show-digest` → clean JSON on stdout, all banners → stderr. Use this when the output is consumed by an agent.

---

## 📊 Scoring System

Each job is independently scored 0–10 on six axes, then combined into a final score:

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
├── src/
│   ├── sources/              # Job board adapters
│   │   ├── arbeitsagentur.py # Bundesagentur für Arbeit (DE)
│   │   ├── jobspy_adapter.py # Indeed + Glassdoor + Google
│   │   ├── bosszhipin.py     # BOSS直聘 (CN)
│   │   ├── lagou.py          # 拉勾网 (CN)
│   │   └── zhilian.py        # 智联招聘 (CN)
│   ├── outputs/
│   │   ├── excel_manager.py  # Excel tracker
│   │   ├── digest_generator.py
│   │   └── application_gen.py # Cover letters
│   ├── query_builder.py      # CV → search queries (EN/DE/CN)
│   ├── scorer.py             # LLM scoring engine (batched)
│   ├── cv_parser.py          # CV → structured profile
│   └── main.py               # CLI entry point
├── docs/
│   └── GUIDE_OPENCLAW_CLAUDE.md
├── config.example.yaml       # Annotated config template
├── cv/                       # Your CV (gitignored)
├── memory/                   # Runtime cache (gitignored)
│   └── job_pool.json
└── outputs/                  # Results (gitignored)
    ├── jobs_pipeline.xlsx
    ├── digests/
    └── applications/
```

---

## 🗺️ Roadmap

- [x] Parallel source crawling (ThreadPoolExecutor)
- [x] `--status` / `--health` / `--json` for agent consumption
- [x] `--init` non-interactive bootstrap
- [x] Negative keyword & company filters
- [x] CV from URL (PDF / HTML / Markdown / DOCX)
- [ ] StepStone full implementation
- [ ] XING native adapter
- [ ] `--preview-score` for prompt debugging
- [ ] 前程无忧 (51job) CN source
- [ ] MCP server mode (`jobradar serve`)
- [ ] Docker one-liner

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
