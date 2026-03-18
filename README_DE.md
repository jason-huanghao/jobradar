<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603182230148.png" width="140" alt="JobRadar Logo" />

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

> **JobRadar** liest deinen Lebenslauf, durchsucht parallel **7 Jobbörsen** in Deutschland und China, bewertet jede Stelle anhand von 6 Kriterien, generiert maßgeschneiderte Anschreiben und CV-Abschnitte und kann **automatisch bewerben** — auf BOSS直聘 und LinkedIn.

---

<div align="center">

| 💬 Community & Feedback | ☕ Projekt unterstützen |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| WeChat folgen · Feedback senden | WeChat Pay · Alipay — oder einfach ⭐ geben |

</div>

---

## ⚡ Null-Konfiguration mit OpenClaw — 1 Nachricht. Fertig.

**Schritt 1 — Installieren** (einmal im Terminal ausführen oder OpenClaw bitten):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
```
Klont automatisch, erstellt Virtualenv, installiert Abhängigkeiten, startet OpenClaw-Gateway neu.

**Schritt 2 — Verwenden** (zu OpenClaw oder Claude sagen):
```
Such Jobs in Deutschland. Mein Lebenslauf: https://github.com/…
```

Dann sagen: *"Such Jobs in Deutschland. Mein Lebenslauf: https://github.com/…"*

Agent führt aus: `setup` → scrapt 36+ Stellen → AI-Scoring → veröffentlicht HTML-Report auf GitHub Pages — **in einer Nachricht, ohne Konfigurationsdateien**.

> 📄 Live-Beispiel: [report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---

## ✨ Funktionen

| Funktion | Was du bekommst |
|----------|----------------|
| 🌐 **7 Quellen parallel** | Bundesagentur, Indeed, Glassdoor, Google Jobs, StepStone, XING, BOSS直聘, 拉勾网, 智联招聘 |
| 🤖 **KI-Matching** | 6-Dimensionen-Score (0–10) mit vollständiger Begründung |
| 🔑 **Automatische API-Erkennung** | OpenClaw-Auth, Claude OAuth oder Umgebungsvariablen |
| 🔌 **Jedes LLM, kein Lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama |
| ✉️ **Individuelle Anschreiben** | Firmenbezogen, LLM-generiert — keine Templates |
| 📝 **Lebenslauf-Abschnitt-Optimierung** | Schreibt deinen Summary + Skills-Abschnitt pro Job neu |
| 📊 **HTML-Report + Excel** | GitHub Pages Report + farbkodierter Excel-Tracker |
| 🚀 **Auto-Bewerbung** | BOSS直聘 Playwright-Gruß + LinkedIn Easy Apply (benötigt `[apply]`) |
| 🌐 **Web-Dashboard** | FastAPI-Oberfläche — Jobs durchsuchen, Bewerbungen generieren, Excel herunterladen |
| ⚡ **Inkrementell** | Nur neue Stellen werden bewertet — tägliche Updates in Minuten |

---

## ⚙️ So funktioniert's

```
Dein Lebenslauf (Markdown / PDF / DOCX / URL)
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ 1  ENTDECKEN  CV parsen → Zielrollen, Skills, Orte │
├─────────────────────────────────────────────────────┤
│ 2  SUCHEN     7 Quellen parallel:                   │
│               Bundesagentur · Indeed · Glassdoor    │
│               Google Jobs · StepStone · XING  (DE) │
│               BOSS直聘 · 拉勾网 · 智联招聘  (CN)    │
├─────────────────────────────────────────────────────┤
│ 3  FILTERN    URL-Dedup · Praktika/Rauschen filtern │
├─────────────────────────────────────────────────────┤
│ 4  BEWERTEN   LLM: 6 Dimensionen (0–10) pro Stelle │
├─────────────────────────────────────────────────────┤
│ 5  GENERIEREN ✉️  Anschreiben pro Top-Match         │
│               📝 CV-Abschnitt pro Top-Match         │
├─────────────────────────────────────────────────────┤
│ 6  AUSGEBEN   📊 HTML-Report · 📁 Excel             │
│               🌐 Web-Dashboard · 🚀 Auto-Bewerbung  │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Schnellstart

### Schnellste Installation (ein Befehl)
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
```

### Manuelle Installation
```bash
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .
# pip install -e ".[cn]"       # CN-Quellen
# pip install -e ".[apply]"    # Auto-Bewerbung
```

### Lebenslauf angeben (alle Formate unterstützt)
```bash
# URL (GitHub, Direktlink, beliebige HTTPS-URL)
jobradar init --cv https://github.com/du/repo/blob/main/cv.md

# Lokale Datei (.md, .pdf, .docx, .txt)
jobradar init --cv /Pfad/zu/cv.pdf

# Interaktiver Wizard (inkl. Text-Einfügen-Option)
jobradar init
```

### Erster Lauf
```bash
export OPENAI_API_KEY=sk-…         # oder ARK_API_KEY, DEEPSEEK_API_KEY
jobradar health                    # Verbindung prüfen
jobradar run --mode quick          # ~3 Min. Schnelltest pip install -e ".[cn]"
# Auto-Bewerbung: pip install -e ".[apply]"

# 2 — API-Schlüssel setzen (einer genügt)
export OPENAI_API_KEY=sk-…
# export ARK_API_KEY=…   export DEEPSEEK_API_KEY=…

# 3 — Setup-Wizard
jobradar init
# Oder nicht-interaktiv:
jobradar init --cv ./cv/cv.md --api-key ARK_API_KEY=xxx --locations "Berlin,Remote" -y

# 4 — Verbindung prüfen
jobradar health

# 5 — Ersten Lauf starten
jobradar run --mode quick           # ~3 Min., Schnelltest
jobradar run                        # Vollständiger Lauf
jobradar install-agent              # Täglich 08:00 (macOS launchd)
```

---

## 🔌 Jobquellen

Alle DE-Quellen sind **vollständig implementiert** — kein Playwright oder Login nötig:

| Quelle | Auth | Hinweis |
|--------|------|---------|
| Bundesagentur für Arbeit | keine | Offizielle DE-API |
| Indeed DE | keine | via python-jobspy |
| Glassdoor DE | keine | via python-jobspy |
| Google Jobs | keine | via python-jobspy |
| StepStone | keine | httpx + BeautifulSoup-Scraper |
| XING | keine | httpx + BeautifulSoup-Scraper |
| BOSS直聘 (CN) | Cookie | `BOSSZHIPIN_COOKIES` — `[cn]`-Extra erforderlich |
| 拉勾网 (CN) | keine | Mobile-API → AJAX → Playwright |
| 智联招聘 (CN) | keine | REST-API → Playwright |

---

## 🔌 LLM-Anbieter

Automatisch in dieser Prioritätsreihenfolge erkannt:

| Priorität | Quelle | Umgebungsvariable |
|-----------|--------|-------------------|
| 0 | **OpenClaw auth-profiles** | automatisch |
| 1 | **Claude OAuth** | automatisch |
| 2 | Volcengine Ark | `ARK_API_KEY` |
| 3 | Z.AI | `ZAI_API_KEY` |
| 4 | OpenAI | `OPENAI_API_KEY` |
| 5 | DeepSeek | `DEEPSEEK_API_KEY` |
| 6 | OpenRouter | `OPENROUTER_API_KEY` |
| 7 | Ollama / LM Studio | *(lokal)* |

---

## 🖥️ Befehlsreferenz

```bash
jobradar init [--cv …] [--api-key ENV=val] [-y]  # Setup-Wizard
jobradar health / status                          # Checks
jobradar run [--mode quick|dry-run|score-only]    # Pipeline
jobradar run --limit 5                            # Ergebnisse begrenzen
jobradar report [--publish] [--min-score 7]       # HTML-Report
jobradar apply [--dry-run] [--auto] [--min-score 8]  # Auto-Bewerbung
jobradar web [--port 8080]                        # Web-Dashboard
jobradar install-agent                            # Tägliche Automation
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

Score ≥ `min_score_application` → Anschreiben + optimierter CV-Abschnitt automatisch generiert.

---

## 🤖 Auto-Bewerbung

Benötigt: `pip install -e ".[apply]" && playwright install chromium`

**BOSS直聘:** Öffnet Stellenseite, prüft HR-Aktivität (> 7 Tage inaktiv → überspringen), klickt 立即沟通, sendet anpassbare Begrüßungsnachricht. Zufällige Verzögerung 3–8 s, max. 50/Tag.

**LinkedIn Easy Apply:** Klickt Easy Apply, reicht einstufige Bewerbungen ein (mehrstufige übersprungen). Zufällige Verzögerung 4–10 s, max. 25/Tag.

```bash
jobradar apply --dry-run            # Zuerst Vorschau
jobradar apply --auto --min-score 8 # Dann live bewerben
```

---

## 🗺️ Roadmap

- [x] 7 parallele Quellen · AI-Scoring (6D) · Anschreiben + CV-Optimierung
- [x] StepStone & XING — vollständige Scraper
- [x] BOSS直聘 Auto-Bewerbung + LinkedIn Easy Apply
- [x] HTML-Report + GitHub Pages · Excel-Export · Web-Dashboard
- [x] OpenClaw Null-Konfiguration
- [ ] 前程无忧 (51job) · Telegram/E-Mail-Digest · Docker · MCP-Server

---

## ⚠️ Haftungsausschluss

Ausschließlich für **persönliche Jobsuche, Lernen und Forschung**. `robots.txt` und Nutzungsbedingungen jeder Plattform einhalten.

---

## 📄 Lizenz

GNU General Public License v3.0 — siehe [LICENSE](LICENSE)

---

<div align="center">

Mit ❤️ für Jobsuchende auf dem deutschen und chinesischen Tech-Markt

**⭐ Falls JobRadar dir zu Vorstellungsgesprächen verholfen hat — ein Stern bedeutet viel.**

</div>
