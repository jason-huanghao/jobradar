# ⚡ JobRadar

> AI-powered job search agent for Germany & China tech roles — scrape, score, apply.

JobRadar fetches job listings from multiple sources, scores them against your CV using an LLM, and generates tailored cover letters + optimized CV sections for top matches. Runs as a CLI tool, a web dashboard, or an OpenClaw AI skill.

[![CI](https://github.com/jason-huanghao/jobradar/actions/workflows/ci.yml/badge.svg)](https://github.com/jason-huanghao/jobradar/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

---

## ✨ Features

- **Multi-source scraping** — Arbeitsagentur, Indeed, Google Jobs, BOSS直聘, 拉勾, 智联招聘
- **LLM scoring** — 6-dimension match scoring (skills, seniority, location, language, visa, growth)
- **Auto-generation** — tailored CV summaries and cover letters for top matches
- **Web dashboard** — Alpine.js SPA with live pipeline progress via WebSocket
- **OpenClaw skill** — use as a natural-language job search agent
- **Zero lock-in** — works with Volcengine Ark, OpenAI, DeepSeek, Ollama, or any OpenAI-compatible API

---

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e ".[all]"
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:
- Set `candidate.cv_path` to your CV file (`.md`, `.pdf`, `.docx`, or `.txt`)
- Set `search.locations` to your target cities
- Enable/disable sources under `sources:`

### 3. Set your LLM API key

```bash
# Create .env file
echo "ARK_API_KEY=your_key_here" > .env

# Or use any other provider:
# echo "OPENAI_API_KEY=sk-..." > .env
# echo "DEEPSEEK_API_KEY=..." > .env
# echo "ZAI_API_KEY=..." > .env
```

Supported providers: **Volcengine Ark**, **OpenAI**, **DeepSeek**, **Z.AI**, **Ollama**, **LM Studio**, **OpenRouter**, **Anthropic**

### 4. Run

```bash
# Fetch and score jobs
jobradar update

# Open the web dashboard
jobradar web
# → http://localhost:7842
```

---

## 📺 Web Dashboard

```bash
jobradar web
```

Features:
- Live pipeline progress via WebSocket
- Job table with filter/sort by score, source, status
- Score breakdown: skills · seniority · location · language · visa · growth
- One-click CV + cover letter generation
- Status tracking: new → interested → applied → interview
- Excel export and Markdown digest

---

## 🖥️ CLI Reference

```bash
jobradar update               # Run full pipeline (fetch + score + generate)
jobradar update --mode quick  # Fewer queries, faster
jobradar update --mode score-only  # Re-score existing DB jobs
jobradar update --mode dry-run    # Validate config only, no network
jobradar web                  # Start dashboard at http://localhost:7842
jobradar status               # Show DB stats
jobradar setup                # Copy config.example.yaml → config.yaml
jobradar install-agent        # Install macOS launchd daily agent
```

---

## 📦 Sources

| Source | Region | Auth required |
|--------|--------|---------------|
| Arbeitsagentur | 🇩🇪 Germany | None |
| Indeed (via jobspy) | 🌍 EU/Global | None |
| Google Jobs (via jobspy) | 🌍 EU/Global | None |
| BOSS直聘 | 🇨🇳 China | Cookie (see below) |
| 拉勾网 | 🇨🇳 China | Auto-fetched |
| 智联招聘 | 🇨🇳 China | None |
| StepStone | 🇩🇪 Germany | Stub (PR welcome) |
| XING | 🇩🇪 Germany | Stub (PR welcome) |

### BOSS直聘 cookie setup

1. Log in at [zhipin.com](https://www.zhipin.com) in Chrome
2. Open DevTools → Application → Cookies
3. Copy `__zp_stoken__` and `wt2` values
4. Add to `.env`: `BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"`

---

## 🤖 OpenClaw Skill

See **[SKILL.md](SKILL.md)** for full installation instructions.

```bash
# Quick install as OpenClaw skill
pip install -e ".[all]"
cp config.example.yaml config.yaml
# Edit config.yaml, then:
jobradar web  # starts the skill server
```

Available tools: `run_pipeline`, `list_jobs`, `get_job_detail`, `generate_application`, `get_digest`, `get_status`

---

## ⚙️ Configuration

All options documented in [`config.example.yaml`](config.example.yaml).

Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `candidate.cv_path` | `./cv/cv_current.md` | Path to your CV |
| `search.locations` | `[Hannover, Berlin, Remote]` | Target cities |
| `search.max_days_old` | `14` | Only fetch recent jobs |
| `search.exclude_keywords` | `[Praktikum, Werkstudent, ...]` | Pre-filter titles |
| `scoring.min_score_application` | `7.0` | Auto-generate docs above this |
| `sources.arbeitsagentur.enabled` | `true` | Enable/disable each source |
| `server.port` | `7842` | Dashboard port |
| `llm.text.provider` | `volcengine` | LLM provider |

---

## 🗃️ Architecture

```
jobradar/
├── src/jobradar/
│   ├── config.py           AppConfig — YAML + env loading
│   ├── pipeline.py         Main orchestrator
│   ├── models/             Pydantic models (RawJob, CandidateProfile, ...)
│   ├── profile/            CV reading + LLM extraction
│   ├── sources/            Job scrapers (adapters per platform)
│   ├── scoring/            Hard filter + LLM scorer + CV/letter generators
│   ├── storage/            SQLite via SQLModel
│   ├── api/                FastAPI app + WebSocket + Alpine.js dashboard
│   └── interfaces/         Typer CLI + OpenClaw skill wrapper
├── config.example.yaml
├── SKILL.md
└── pyproject.toml
```

Pipeline flow:
```
CV → profile extraction → query builder → parallel scrape
  → dedup → hard filter → LLM scoring → CV/letter generation → dashboard
```

---

## 🛠️ Development

```bash
pip install -e ".[dev]"
ruff check src/
pytest tests/
```

---

## 📄 License

GPL-3.0 — see [LICENSE](LICENSE)

---

## 🤝 Contributing

PRs welcome, especially for:
- StepStone and XING adapters
- LinkedIn scraper improvements
- Additional LLM provider support
- Test coverage
