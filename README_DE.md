<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### Schluss mit blindem Bewerben. Lass KI die richtigen Jobs für dich finden.

[![GitHub Stars](https://img.shields.io/github/stars/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/network)
[![GitHub Issues](https://img.shields.io/github/issues/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/issues)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*Ein [OpenClaw](https://openclaw.ai)-Skill — eigenständig oder in jeden KI-Agenten einbettbar*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** liest deinen Lebenslauf, durchsucht parallel 7 Jobbörsen in Deutschland und China, bewertet jede Stelle mit einem LLM anhand von 6 Kriterien und liefert täglich eine Zusammenfassung, HTML-Report und maßgeschneiderte Bewerbungsschreiben — vollautomatisch.

---

<div align="center">

| 💬 Community & Feedback | ☕ Projekt unterstützen |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| WeChat folgen · Feedback senden | WeChat Pay · Alipay — oder einfach ⭐ geben |

</div>

---

## ⚡ Null-Konfiguration mit OpenClaw — 1 Nachricht. Fertig.

Wenn du [OpenClaw](https://openclaw.ai) verwendest, wird JobRadar als Skill installiert und **benötigt nur deinen Lebenslauf**. Der API-Schlüssel wird automatisch aus deiner OpenClaw-Umgebung erkannt — kein manuelles Konfigurieren nötig.

```bash
# Einmalige Skill-Installation
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && python3 -m venv .venv && .venv/bin/pip install -e . -q
openclaw gateway restart
```

Dann einfach sagen:

```
Such mir Jobs in Deutschland. Mein Lebenslauf: https://github.com/du/repo/blob/main/cv.md
```

Der Agent ruft `setup` auf (API-Schlüssel automatisch erkannt), crawlt 36+ Stellen, bewertet sie mit KI und veröffentlicht einen HTML-Report auf GitHub Pages — **in zwei Gesprächsrunden, null Konfigurationsdateien**.

> 📄 Live-Beispiel: [report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---

## 📋 Navigation

| [✨ Funktionen](#-funktionen) | [⚙️ So funktioniert's](#️-so-funktionierts) | [🚀 Schnellstart](#-schnellstart) |
|:---:|:---:|:---:|
| [🤖 Mit OpenClaw & Claude](#-mit-openclaw--claude) | [🔌 Jobquellen](#-jobquellen) | [🔌 LLM-Anbieter](#-llm-anbieter) |
| [⚙️ Konfiguration](#️-konfiguration) | [🖥️ Befehlsreferenz](#️-befehlsreferenz) | [📊 Bewertungssystem](#-bewertungssystem) |
| [🗺️ Roadmap](#️-roadmap) | [🤝 Mitmachen](#-mitmachen) | [⚠️ Haftungsausschluss](#️-haftungsausschluss) |

---

## ✨ Funktionen

| Funktion | Was du bekommst |
|----------|----------------|
| 🌐 **7 Quellen parallel** | Bundesagentur, Indeed, Glassdoor, Google Jobs, StepStone, BOSS直聘, 拉勾网, 智联招聘 — gleichzeitig |
| 🤖 **KI-Matching** | 6-Dimensionen-Score (0–10) mit vollständiger Begründung |
| 🔑 **Automatische API-Erkennung** | OpenClaw-Auth, Claude OAuth oder Umgebungsvariablen — kein manuelles Eingeben |
| 🔌 **Jedes LLM, kein Lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama — automatisch erkannt |
| 📊 **HTML-Report + Excel** | Farbkodierter Tracker + GitHub Pages Report mit einem Befehl |
| 📰 **Tages-Digest** | Markdown-Zusammenfassung der besten Matches, per E-Mail oder Handy |
| ✉️ **Individuelle Anschreiben** | Firmenbezogen, LLM-generiert — keine Templates |
| ⚡ **Inkrementell** | Nur neue Stellen werden bewertet — tägliche Updates in Minuten |
| 🧠 **Lernende Präferenzen** | `--feedback "AMD liked"` beeinflusst alle künftigen Bewertungen |

---

## ⚙️ So funktioniert's

```
Dein Lebenslauf (Markdown / PDF / DOCX / URL)
              │
              ▼
┌─────────────────────────────────────────────────┐
│ 1  ENTDECKEN  Lebenslauf parsen → Zielrollen    │
│               Suchanfragen pro Plattform bauen  │
├─────────────────────────────────────────────────┤
│ 2  SUCHEN     7 Quellen in parallelen Threads   │
│               Bundesagentur · Indeed · Glassdoor│
│               Google Jobs · StepStone           │
│               BOSS直聘 · 拉勾网 · 智联招聘      │
├─────────────────────────────────────────────────┤
│ 3  FILTERN    URL-Dedup · Praktika herausfiltern│
├─────────────────────────────────────────────────┤
│ 4  BEWERTEN   LLM bewertet jede Stelle (0–10)  │
│               Skills · Seniority · Ort          │
│               Sprache · Visum · Entwicklung     │
├─────────────────────────────────────────────────┤
│ 5  AUSGEBEN   📊 HTML-Report (GitHub Pages)     │
│               📰 Tages-Digest                   │
│               ✉️  Anschreiben · 📧 E-Mail-Alert  │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Schnellstart

```bash
# 1 — Klonen & installieren
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — LLM-Schlüssel setzen (einer genügt)
export OPENAI_API_KEY=sk-…
# export DEEPSEEK_API_KEY=…         # günstigste Option
# export ARK_API_KEY=…              # Volcengine Ark

# 3 — Einrichten (schreibt config.yaml automatisch)
jobradar --init --cv ./cv/cv_current.md --locations "Berlin,Hamburg,Remote"

# 4 — Verbindung prüfen
jobradar --health

# 5 — Erster Lauf
jobradar --mode quick               # ~3 Min., 2 Quellen — zum Testen
jobradar --update                   # Vollständiger inkrementeller Lauf
jobradar --install-agent            # Täglich um 8 Uhr automatisieren
```

---

## 🤖 Mit OpenClaw & Claude

**API-Schlüssel wird automatisch erkannt** — der Agent braucht nur deine Lebenslauf-URL.

| Du sagst | Was ausgeführt wird |
|----------|---------------------|
| „Such Jobs in DE. Mein CV: https://…" | `setup` + `run_pipeline` + `list_jobs` |
| „Ist JobRadar bereit?" | `--health --json` |
| „Zeig mir die besten Jobs heute" | `--show-digest --json` |
| „Anschreiben für SAP erstellen" | `--generate-app "SAP"` |
| „Ich habe mich bei Zalando beworben" | `--mark-applied "Zalando"` |
| „Warum hat Databricks niedrig gescort?" | `--explain "Databricks"` |
| „Report veröffentlichen" | `get_report --publish` → GitHub Pages URL |
| „Tägliche Automation einrichten" | `--install-agent` |

---

## 🔌 Jobquellen

| Quelle | Status | Authentifizierung |
|--------|--------|-------------------|
| Bundesagentur für Arbeit | ✅ Aktiv | Keine |
| Indeed DE | ✅ Aktiv | Keine |
| Glassdoor DE | ✅ Aktiv | Keine |
| Google Jobs | ✅ Aktiv | Keine |
| StepStone | 🔧 In Entwicklung | — |
| XING | 🔧 In Entwicklung | Apify Token |
| BOSS直聘 (CN) | ✅ Aktiv | Browser-Cookie + CN IP |
| 拉勾网 (CN) | ✅ Aktiv | Session-Cookie (auto) |
| 智联招聘 (CN) | ✅ Aktiv | Kein Login nötig |

---

## 🔌 LLM-Anbieter

Wird automatisch in dieser Reihenfolge erkannt:

| Priorität | Quelle | Umgebungsvariable |
|-----------|--------|-------------------|
| 0 | **OpenClaw auth-profiles** | automatisch |
| 1 | **Claude OAuth** | automatisch |
| 2 | Volcengine Ark | `ARK_API_KEY` |
| 3 | Z.AI | `ZAI_API_KEY` |
| 4 | OpenAI | `OPENAI_API_KEY` |
| 5 | DeepSeek | `DEEPSEEK_API_KEY` |
| 6 | OpenRouter | `OPENROUTER_API_KEY` |
| 7 | Ollama | *(lokal)* |

---

## ⚙️ Konfiguration

```yaml
candidate:
  cv: "./cv/cv_current.md"
search:
  locations: ["Berlin", "Hamburg", "Remote"]
  exclude_keywords: ["Praktikum", "Werkstudent", "Ausbildung"]
  exclude_companies: ["MeinAlterArbeitgeber"]
scoring:
  min_score_digest: 6
  min_score_application: 7
server:
  db_path: ./jobradar.db
```

---

## 🖥️ Befehlsreferenz

```bash
jobradar --init [--cv …] [--locations …] [--llm …] [--key …]
jobradar --health [--json]          # Verbindungscheck
jobradar --status [--json]          # Pool-Statistiken
jobradar --update                   # Täglicher Lauf (nur neue Stellen)
jobradar --mode quick               # Schnelltest (~3 Min.)
jobradar --show-digest [--json]     # Heutigen Digest anzeigen
jobradar --generate-app "Firma"     # Anschreiben erstellen
jobradar --mark-applied "Firma"     # Als beworben markieren
jobradar --explain "Firma"          # Score-Analyse anzeigen
jobradar --feedback "AMD liked"     # Präferenz speichern
jobradar --install-agent            # Tägliche Automation
```

---

## 📊 Bewertungssystem

| Dimension | Was bewertet wird |
|-----------|------------------|
| **Skills-Match** | Technologie-Stack-Überlappung |
| **Seniority-Fit** | Erfahrungsjahre vs. Rollenlevel |
| **Standort-Fit** | Pendelbarkeit, Remote-Option |
| **Sprach-Fit** | DE/EN-Anforderungen vs. Sprachkenntnisse |
| **Visumsfreundlich** | Wahrscheinlichkeit einer Arbeitserlaubnis |
| **Wachstumspotenzial** | Karrierepfad, Unternehmenstrajektorie |

---

## 🗺️ Roadmap

- [x] Paralleles Crawling · `--health` / `--status` / `--json`
- [x] `--init` nicht-interaktives Setup
- [x] OpenClaw Null-Konfiguration (API-Schlüssel automatisch erkannt)
- [x] HTML-Report + GitHub Pages Publisher
- [x] Alle Pfade relativ (kein `~/.jobradar`)
- [ ] StepStone vollständige Implementierung
- [ ] XING / LinkedIn nativer Adapter
- [ ] Docker-Einzeiler · OpenClaw Cron-Integration

---

## 🤝 Mitmachen

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ && pytest tests/ -v
```

---

## ⚠️ Haftungsausschluss

Ausschließlich für **persönliche Jobsuche, technisches Lernen und akademische Forschung**. Nutzer müssen die `robots.txt` und Nutzungsbedingungen jeder Plattform einhalten.

---

## 📄 Lizenz

GNU General Public License v3.0 — siehe [LICENSE](LICENSE)

---

<div align="center">

Mit ❤️ für Jobsuchende auf dem deutschen und chinesischen Tech-Markt

**⭐ Falls JobRadar dir zu Vorstellungsgesprächen verholfen hat — ein Stern bedeutet viel.**

</div>
