<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### AI-powered job search agent for Germany & China tech roles

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

> **JobRadar** reads your CV, searches 7 job platforms across Europe and China simultaneously, uses an LLM to score each role on 6 dimensions, and delivers a daily digest + Excel tracker + cover letters — fully automated. Just drop your CV in and let it run.

---

## 📋 Table of Contents

1. [Features](#-features)
2. [How It Works](#-how-it-works)
3. [Quick Start](#-quick-start)
4. [Using with OpenClaw & Claude](#-using-with-openclaw--claude)
5. [Job Sources](#-job-sources)
6. [LLM Providers](#-llm-providers)
7. [Configuration](#-configuration)
8. [CLI Reference](#-cli-reference)
9. [Scoring System](#-scoring-system)
10. [Project Structure](#-project-structure)
11. [Roadmap](#-roadmap)
12. [Contributing](#-contributing)
13. [Community & Feedback](#-community--feedback)
14. [Support This Project](#-support-this-project)
15. [Disclaimer](#-disclaimer)

---

## ✨ Features

| Feature | Detail |
|---------|--------|
| 🌐 **7 job sources** | Bundesagentur, Indeed, Glassdoor, StepStone, BOSS直聘, 拉勾网, 智联招聘 |
| 🤖 **LLM scoring** | 6-dimension fit score (0–10) per job, with reasoning in your language |
| 🔌 **Any LLM** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama — zero lock-in |
| 📊 **Excel tracker** | Colour-coded by score, applied status, one-click filter |
| 📰 **Daily digest** | Markdown summary of top matches, ready to paste anywhere |
| ✉️ **Cover letters** | Auto-generated, personalised per company via LLM |
| 📧 **Email alert** | SMTP digest push (Gmail App Password supported) |
| ⚡ **Incremental** | Only scores truly new jobs — daily runs finish in minutes |
| 🧠 **Feedback loop** | `--feedback "AMD liked"` biases future scoring |
| 🤝 **Agent-ready** | CLI tool or OpenClaw/Claude Code skill |


---

## ⚙️ How It Works

```
Your CV (Markdown / PDF / DOCX)
         │
         ▼
┌────────────────────────────────────────────────────┐
│ 1  DISCOVER  Parse CV with LLM → extract roles,   │
│              skills, preferences, target locations │
│              Build platform-specific search queries│
├────────────────────────────────────────────────────┤
│ 2  CRAWL     Bundesagentur für Arbeit (DE)         │
│              Indeed · Glassdoor · Google Jobs      │
│              StepStone (DE)                        │
│              BOSS直聘 · 拉勾网 · 智联招聘 (CN)     │
├────────────────────────────────────────────────────┤
│ 3  SCORE     LLM rates each job on 6 axes (0–10): │
│              Skills match · Seniority fit          │
│              Location · Language · Visa · Growth   │
├────────────────────────────────────────────────────┤
│ 4  DELIVER   📊 Excel tracker (colour-coded)       │
│              📰 Daily Markdown digest              │
│              ✉️  Cover letter per company          │
│              📧 Email push alert                   │
└────────────────────────────────────────────────────┘
          ↑
          └── Feedback loop: your ratings refine
              future scoring automatically
```

---

## 🚀 Quick Start

**Prerequisites:** Python 3.11+, one LLM API key, your CV as Markdown/PDF/DOCX.

```bash
# Step 1 — Clone & install
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e .

# Step 2 — Set your LLM key (pick any one)
export ARK_API_KEY=your_volcengine_key   # Volcengine Ark (doubao) — recommended for CN
# export ZAI_API_KEY=…                  # Z.AI
# export OPENAI_API_KEY=sk-…            # OpenAI
# export DEEPSEEK_API_KEY=…             # DeepSeek (cost-effective)

# Step 3 — Interactive setup (creates config.yaml)
jobradar --setup

# Step 4 — Add your CV, then run
cp your_cv.md cv/cv_current.md          # or .pdf / .docx
jobradar --mode quick                   # fast test: ~3 min, 2 sources
jobradar                                # full run: all sources
jobradar --install-agent                # daily 8am automation
```

> **Tip:** Run `jobradar --mode dry-run` first to preview the search queries without hitting any APIs.

---

## 🤖 Using with OpenClaw & Claude

JobRadar is designed to be operated conversationally — you describe what you want, and the agent runs the right command. No YAML editing required.

### Option A — OpenClaw

Place the `jobradar/` folder in your OpenClaw skills directory. OpenClaw reads `SKILL.md` automatically and maps natural language to CLI calls.

**First-time setup — one conversation, zero config files:**

```
You:  Set up JobRadar. My CV is at https://mysite.com/cv.pdf,
      I want AI/ML jobs in Berlin and Hamburg,
      and my OpenAI key is sk-xxxx
```

OpenClaw runs:
```bash
jobradar --init --cv https://mysite.com/cv.pdf \
         --locations "Berlin,Hamburg,Remote" \
         --llm openai --key sk-xxxx
```

This writes `config.yaml` and `.env` — no wizard, no manual editing.

**Verify and run:**

```
You:  Check if JobRadar is ready
```
→ `jobradar --health --json` — checks LLM latency, source reachability, CV presence

```
You:  Find me AI jobs now
```
→ `jobradar --mode quick` (fast: 2 sources, ~3 min)

```
You:  Show me today's top matches
```
→ `jobradar --show-digest --json` — results presented inline

```
You:  What's in my job pool?
```
→ `jobradar --status --json`:
```json
{
  "pool": { "total": 312, "scored": 298, "unscored": 14 },
  "top_job": { "title": "ML Engineer", "company": "DeepL", "score": 8.4 },
  "sources": { "arbeitsagentur": "enabled", "indeed": "enabled" }
}
```

**Act on results:**

| You say | Command |
|---------|---------|
| "Write a cover letter for DeepL" | `jobradar --generate-app "DeepL"` |
| "I applied to Zalando" | `jobradar --mark-applied "Zalando"` |
| "Why did Databricks score low?" | `jobradar --explain "Databricks"` |
| "I liked that AMD role" | `jobradar --feedback "AMD liked"` |
| "Set up daily search" | `jobradar --install-agent` |

---

### Option B — Claude Code

Open the project directory in Claude Code. It reads `CLAUDE.md` automatically.

```bash
# In Claude Code terminal — set up and run
jobradar --init --cv ./cv/cv_current.md --llm openai --key $OPENAI_API_KEY
jobradar --health
jobradar --mode quick
```

Or just ask naturally:
```
"My CV is at ~/Downloads/resume.pdf — set up JobRadar and find ML jobs in Munich"
"Run my daily job search and show me the results"
"Generate a cover letter for the Siemens job"
```

---

### Option C — Claude (claude.ai + Desktop Commander or Filesystem MCP)

With Desktop Commander or the Filesystem MCP connected:

```
"Set up JobRadar. CV URL: https://… OpenAI key: sk-…"
```

Claude runs `jobradar --init …` then `jobradar --health` to verify.

Daily usage works the same as OpenClaw — just ask conversationally.

---

### Minimum config (13 lines)

The `--init` command generates this automatically. Everything else is optional:

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

`.env` file (same directory):
```
OPENAI_API_KEY=sk-your-key-here
```

> 📖 **Full guide:** [docs/GUIDE_OPENCLAW_CLAUDE.md](docs/GUIDE_OPENCLAW_CLAUDE.md)

---

## 🔌 Job Sources

### 🇩🇪 Europe (Germany focus)

| Source | Platform | Status | Auth |
|--------|----------|--------|------|
| **Bundesagentur für Arbeit** | Official DE job board | ✅ Active | None |
| **Indeed DE** | Global job board | ✅ Active | None |
| **Glassdoor DE** | Jobs + company reviews | ✅ Active | None |
| **Google Jobs** | Aggregated global | ✅ Active | None |
| **StepStone** | DE job board | 🔧 Stub | — |
| **XING** | DACH professional | 🔧 Stub | Apify token |
| **LinkedIn** | Global | 🔧 Planned | — |

### 🇨🇳 China

| Source | Platform | Status | Auth |
|--------|----------|--------|------|
| **BOSS直聘** | Top CN tech jobs | ✅ Active | Browser cookie + CN IP |
| **拉勾网** | Tech-focused jobs | ✅ Active | Session cookie (auto) + CN IP |
| **智联招聘** | Large general board | ✅ Active | None (CN IP recommended) |

> **Note:** Chinese platforms work best from a Chinese IP address. From Europe, use a VPN or run JobRadar on a CN cloud server (e.g. Alibaba Cloud ECS) for CN job searches.

To enable Chinese platforms, add Chinese cities to your config:

```yaml
search:
  locations: ["Hannover", "Berlin", "Remote", "上海", "北京"]

sources:
  zhilian:   { enabled: true }   # no auth needed
  lagou:     { enabled: true }   # auto-fetches cookies
  bosszhipin:
    enabled: true                # requires cookie — see setup below
```

**BOSS直聘 cookie setup** (one-time, ~2 min):
1. Log in to [zhipin.com](https://www.zhipin.com) in Chrome
2. DevTools → **Application → Cookies → www.zhipin.com**
3. Copy `__zp_stoken__` and `wt2`
4. `export BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"`

---

## 🤖 LLM Providers

JobRadar auto-detects the first available key at startup — no config change needed if your key is already in the environment:

| Priority | Provider | Env Var | Best for |
|----------|----------|---------|----------|
| 1 | config.yaml explicit | — | Pinning a specific model |
| 2 | **Volcengine Ark** | `ARK_API_KEY` | CN users, doubao models |
| 3 | **Z.AI** | `ZAI_API_KEY` | — |
| 4 | **OpenAI** | `OPENAI_API_KEY` | GPT-4o |
| 5 | **DeepSeek** | `DEEPSEEK_API_KEY` | Cost-effective |
| 6 | **OpenRouter** | `OPENROUTER_API_KEY` | Model aggregator |
| 7 | **Ollama** | *(local)* | Fully offline |

All providers use the same OpenAI-compatible interface. To switch, just change `base_url` + `api_key_env` in `config.yaml`.

---

## ⚙️ Configuration

```bash
cp config.example.yaml config.yaml
# Edit config.yaml — never commit it (gitignored)
```

Key sections at a glance:

```yaml
candidate:
  cv_path: "./cv/cv_current.md"    # supports .md, .pdf, .docx

search:
  locations: ["Hannover", "Berlin", "Remote"]
  radius_km: 50
  max_results_per_source: 50
  max_days_old: 14

scoring:
  min_score_digest: 6              # show in daily digest
  min_score_application: 7         # auto-generate cover letter

llm:
  text:
    provider: "volcengine"
    model: "doubao-seed-2.0-code"
    api_key_env: "ARK_API_KEY"
```

Full annotated reference: [`config.example.yaml`](config.example.yaml)


---

## 🖥️ CLI Reference

```bash
# ── First-time setup ──────────────────────────────────────────────
jobradar --init                    # Non-interactive bootstrap (agent-friendly)
jobradar --setup                   # Interactive setup wizard
jobradar --install-agent           # Install launchd/cron at 8am
jobradar --uninstall-agent         # Remove scheduled job

# ── Inspect ───────────────────────────────────────────────────────
jobradar --health [--json]         # Check LLM + source connectivity
jobradar --status [--json]         # Pool stats + source readiness

# ── Pipeline ──────────────────────────────────────────────────────
jobradar                           # Full pipeline (crawl + score + output)
jobradar --update                  # Incremental: new jobs only + email
jobradar --mode quick              # Fast test (BA + Indeed only, ~3 min)
jobradar --mode dry-run            # Show queries, don't execute
jobradar --crawl-only              # Crawl only (no scoring)
jobradar --score-only              # Score unscored jobs + output
jobradar --rerun-scoring           # Clear scores + re-score everything
jobradar --parse-cv-only           # CV → JSON debug output
jobradar --cv PATH_OR_URL          # Override CV for this run

# ── Conversational (OpenClaw / Claude) ───────────────────────────
jobradar --show-digest [--json]    # Print today's top jobs
jobradar --generate-app "AMD"      # Cover letter for AMD role
jobradar --mark-applied "SAP"      # Mark SAP job as applied
jobradar --explain "Databricks"    # Show LLM score breakdown
jobradar --feedback "AMD liked"    # Record preference for future scoring
```

> Add `--json` to `--status`, `--health`, or `--show-digest` for clean JSON output on stdout — all banners go to stderr so agents can parse results directly.

---

## 📊 Scoring System

Each job is scored 0–10 on six independent axes, then combined into a final weighted score:

| Dimension | What it measures |
|-----------|-----------------|
| **Skills match** | Technical stack overlap (languages, frameworks, tools) |
| **Seniority fit** | Years of experience vs. role level (junior/mid/senior/lead) |
| **Location fit** | Commute feasibility, remote-first, relocation requirement |
| **Language fit** | German/English requirements vs. your proficiency |
| **Visa friendly** | Likelihood of work permit sponsorship |
| **Growth potential** | Domain relevance, team size, learning opportunities |

Jobs scoring ≥ `min_score_digest` appear in your daily digest.
Jobs scoring ≥ `min_score_application` get an auto-generated cover letter.

---

## 🗂️ Project Structure

```
jobradar/
├── src/
│   ├── sources/                   # Job board adapters
│   │   ├── arbeitsagentur.py      # Bundesagentur für Arbeit (DE)
│   │   ├── jobspy_adapter.py      # Indeed + Glassdoor + Google
│   │   ├── stepstone_scraper.py   # StepStone (stub)
│   │   ├── xing_adapter.py        # XING (stub)
│   │   ├── bosszhipin.py          # BOSS直聘 (CN)
│   │   ├── lagou.py               # 拉勾网 (CN)
│   │   └── zhilian.py             # 智联招聘 (CN) — no auth
│   ├── outputs/
│   │   ├── excel_manager.py       # Excel tracker generation
│   │   ├── digest_generator.py    # Markdown daily digest
│   │   └── application_gen.py     # Cover letter generation
│   ├── notifications/
│   │   └── email_notifier.py      # SMTP email digest
│   ├── query_builder.py           # CV → search queries (EN/DE/CN)
│   ├── scorer.py                  # LLM scoring engine (batched)
│   ├── cv_parser.py               # CV → structured profile
│   ├── deduplicator.py            # URL-based dedup + fuzzy merge
│   ├── feedback.py                # Preference learning
│   └── main.py                    # CLI entry point
├── config.example.yaml            # Annotated config template
├── cv/                            # Your CV (gitignored)
│   └── cv_current.md              # Drop your CV here
├── memory/                        # Runtime cache (gitignored)
│   └── job_pool.json              # Persistent job pool
└── outputs/                       # Results (gitignored)
    ├── jobs_pipeline.xlsx
    ├── digests/
    └── applications/
```

---

## 🗺️ Roadmap

- [x] Parallel source crawling (ThreadPoolExecutor, 6 workers)
- [x] `--status` / `--health` inspection commands
- [x] `--init` non-interactive bootstrap for agents
- [x] `--json` flag for machine-readable output
- [x] Negative keyword & company filters
- [ ] StepStone full scraper implementation
- [ ] XING native adapter (no Apify)
- [ ] `--preview-score` for prompt debugging
- [ ] 前程无忧 (51job) CN source
- [ ] MCP server mode (`jobradar serve`)
- [ ] Docker one-liner deployment

---

## 🤝 Contributing

Contributions welcome! Priority areas:

- **Source adapters**: StepStone, XING, LinkedIn full implementations  
- **Tests**: more coverage in `tests/`  
- **Translations**: improve non-English READMEs  

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/           # linting
pytest tests/ -v          # tests
```

---

## ⚠️ Disclaimer

The web scraping functionality in this project is intended **only for personal job search, technical learning, and academic research purposes**.

- Users must comply with each platform's `robots.txt` and Terms of Service
- Do not use this tool for bulk commercial data collection or redistribution  
- Users are solely responsible for any legal consequences arising from their use
- This project has no affiliation with any of the job platforms listed

---

## 💬 Community & Feedback

Found a bug, have a feature request, or just want to share that you landed a job with JobRadar?

**WeChat Public Account** — follow for updates, tips, and to leave feedback directly:

<div align="center">
<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101718363.png" width="200" alt="WeChat Public Account" />
<br/><em>Scan to follow · Send a message to leave feedback</em>
</div>

You're also welcome to open a [GitHub Issue](https://github.com/jason-huanghao/jobradar/issues) or start a [Discussion](https://github.com/jason-huanghao/jobradar/discussions).

---

## ☕ Support This Project

JobRadar is free and open-source. If it saved you time or helped you land interviews, a small token of appreciation keeps the project going — covering server costs, API fees for testing, and late-night coffee.

<div align="center">
<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101748931.png" width="360" alt="WeChat Pay & Alipay" />
<br/><em>WeChat Pay &nbsp;·&nbsp; Alipay</em>
</div>

No pressure at all — starring the repo and sharing it with a friend who's job hunting means just as much. 🌟

---

## 📄 License

GNU General Public License v3.0 — see [LICENSE](LICENSE)

---

<div align="center">

Made with ❤️ for job hunters navigating Germany and China tech markets

⭐ Star this repo if JobRadar helped you land interviews!

</div>
