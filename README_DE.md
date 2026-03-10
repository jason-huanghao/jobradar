<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### Schluss mit blindem Bewerben. Lass KI die richtigen Jobs für dich finden.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*Ein [OpenClaw](https://openclaw.ai)-Skill — eigenständig oder in jeden KI-Agenten einbettbar*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** liest deinen Lebenslauf, durchsucht parallel 7 Jobbörsen in Deutschland und China, bewertet jede Stelle mit einem LLM anhand von 6 Kriterien und liefert täglich eine Zusammenfassung, Excel-Tracker und maßgeschneiderte Bewerbungsschreiben — vollautomatisch.

---

<div align="center">

| 💬 Community & Feedback | ☕ Projekt unterstützen |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="160" alt="WeChat Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Pay & Alipay" /> |
| WeChat folgen · Feedback senden | WeChat Pay · Alipay — oder einfach ⭐ geben |

</div>

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
| 🔌 **Jedes LLM, kein Lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama — automatisch erkannt |
| 📊 **Excel-Tracker** | Farbkodiert nach Score, mit Bewerbungsstatus |
| 📰 **Tages-Digest** | Markdown-Zusammenfassung der besten Matches |
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
│               BOSS直聘 · 拉勾网 · 智联招聘      │
├─────────────────────────────────────────────────┤
│ 3  FILTERN    URL-Dedup · Praktika herausfiltern│
│               (kostenlos, vor dem LLM-Scoring)  │
├─────────────────────────────────────────────────┤
│ 4  BEWERTEN   LLM bewertet jede Stelle (0–10)  │
│               Skills · Seniority · Ort          │
│               Sprache · Visum · Entwicklung     │
├─────────────────────────────────────────────────┤
│ 5  AUSGEBEN   Excel · Tages-Digest ·            │
│               Anschreiben · E-Mail-Alert        │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Schnellstart

```bash
# 1 — Klonen & installieren
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — LLM-Schlüssel setzen (einer genügt)
export OPENAI_API_KEY=sk-…          # OpenAI
# export DEEPSEEK_API_KEY=…         # DeepSeek (günstigste Option)
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

| Du sagst | Ausgeführter Befehl |
|----------|---------------------|
| „JobRadar einrichten, mein CV ist bei https://…" | `jobradar --init --cv … --llm … --key …` |
| „Ist JobRadar bereit?" | `jobradar --health --json` |
| „Such mir KI-Jobs in Berlin" | `jobradar --mode quick` |
| „Zeig mir die besten Jobs heute" | `jobradar --show-digest --json` |
| „Anschreiben für DeepL erstellen" | `jobradar --generate-app "DeepL"` |
| „Ich habe mich bei SAP beworben" | `jobradar --mark-applied "SAP"` |
| „Warum hat Databricks niedrig gescort?" | `jobradar --explain "Databricks"` |

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
| 智联招聘 (CN) | ✅ Aktiv | Kein Login |

---

## 🔌 LLM-Anbieter

| Anbieter | Umgebungsvariable | Hinweis |
|----------|-------------------|---------|
| Volcengine Ark | `ARK_API_KEY` | doubao-Modelle |
| Z.AI | `ZAI_API_KEY` | — |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini empfohlen |
| DeepSeek | `DEEPSEEK_API_KEY` | Kostengünstigste Option |
| OpenRouter | `OPENROUTER_API_KEY` | 200+ Modelle |
| Ollama | *(keiner)* | Vollständig lokal |

---

## ⚙️ Konfiguration

```yaml
candidate:
  cv_path: "./cv/cv_current.md"
search:
  locations: ["Berlin", "Hamburg", "Remote"]
  exclude_keywords: ["Praktikum", "Werkstudent", "Ausbildung"]
  exclude_companies: ["MeinAlterArbeitgeber"]
scoring:
  min_score_digest: 6
  min_score_application: 7
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

- [x] Paralleles Crawling (ThreadPoolExecutor)
- [x] `--status` / `--health` / `--json`
- [x] `--init` nicht-interaktives Setup
- [x] Negativ-Filter für Keywords & Unternehmen
- [ ] StepStone vollständige Implementierung
- [ ] XING nativer Adapter
- [ ] Docker-Einzeiler

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
