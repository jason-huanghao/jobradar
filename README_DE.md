<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="120" alt="JobRadar Logo" />

# JobRadar

**KI-gesteuerter Job-Such-Agent für Tech-Stellen in Deutschland und China**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg)](https://openclaw.ai)

*Ein [OpenClaw](https://openclaw.ai)-Skill — eigenständig oder in jeden KI-Agenten integrierbar*

</div>

---

## 🌍 Sprachen

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

---

## Was macht JobRadar?

JobRadar liest deinen Lebenslauf, durchsucht gleichzeitig Jobbörsen in Europa und China, bewertet jede Stelle mit einem KI-Modell anhand von 6 Kriterien und liefert täglich eine Zusammenfassung, einen Excel-Tracker und fertige Bewerbungsanschreiben – vollautomatisch.

```
Dein Lebenslauf (Markdown)
    │
    ▼
┌──────────────────────────────────────────────────┐
│  1. ENTDECKEN   Lebenslauf parsen → Zielrollen   │
│                 Suchanfragen pro Plattform        │
├──────────────────────────────────────────────────┤
│  2. SUCHEN      Bundesagentur · Indeed · Glass-  │
│                 door · StepStone · BOSS直聘 ·    │
│                 拉勾网 · 智联招聘 (7 Quellen)    │
├──────────────────────────────────────────────────┤
│  3. BEWERTEN    KI bewertet jede Stelle (0–10):  │
│                 Skills · Seniority · Ort ·       │
│                 Sprache · Visum · Entwicklung    │
├──────────────────────────────────────────────────┤
│  4. AUSGEBEN    Excel · Tages-Digest ·           │
│                 Anschreiben · E-Mail-Alert        │
└──────────────────────────────────────────────────┘
```

---

## ✨ Funktionen

| Funktion | Details |
|----------|---------|
| **7 Jobquellen** | Bundesagentur, Indeed, Glassdoor, StepStone, BOSS直聘, 拉勾网, 智联招聘 |
| **KI-Bewertung** | 6-Dimensionen-Score (0–10) mit Begründung |
| **Jedes LLM** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama |
| **Excel-Tracker** | Farbkodiert nach Score, mit Bewerbungsstatus |
| **Tages-Digest** | Markdown-Zusammenfassung der besten Matches |
| **Anschreiben** | Automatisch, individuell pro Unternehmen |
| **E-Mail-Alert** | SMTP-Digest (Gmail App-Passwort unterstützt) |
| **Inkrementell** | Bewertet nur wirklich neue Stellen – schnelle Updates |
| **Feedback-Schleife** | `--feedback "AMD liked"` beeinflusst künftige Bewertungen |
| **CLI + Agent** | Kommandozeile oder eingebettet in OpenClaw / Claude Code |

---

## 🚀 Schnellstart

```bash
# 1. Installation
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e .

# 2. LLM-Schlüssel setzen (einer reicht)
export ARK_API_KEY=dein_schluessel    # Volcengine Ark
# export OPENAI_API_KEY=sk-…          # OpenAI
# export DEEPSEEK_API_KEY=…           # DeepSeek

# 3. Einrichtungsassistent starten (erstellt config.yaml)
jobradar --setup

# 4. Lebenslauf in cv/cv_current.md ablegen, dann:
jobradar --mode quick               # Schnelltest (~3 Min.)
jobradar                            # Vollständige Pipeline
jobradar --install-agent            # Täglich um 8 Uhr automatisch
```

---

## 🔌 Jobquellen

### Europa (Schwerpunkt Deutschland)

| Quelle | Plattform | Status |
|--------|-----------|--------|
| Bundesagentur für Arbeit | Offizielle DE-Jobbörse | ✅ Aktiv |
| Indeed DE | via python-jobspy | ✅ Aktiv |
| Glassdoor DE | via python-jobspy | ✅ Aktiv |
| Google Jobs | via python-jobspy | ✅ Aktiv |
| StepStone | DE Jobbörse | 🔧 In Entwicklung |
| XING | DACH Karrierenetzwerk | 🔧 In Entwicklung |

### China

| Quelle | Status | Hinweis |
|--------|--------|---------|
| BOSS直聘 | ✅ Aktiv | Cookie-Einrichtung erforderlich |
| 拉勾网 | ✅ Aktiv | Session-Cookie automatisch |
| 智联招聘 | ✅ Aktiv | Kein Login erforderlich |

---

## 🖥️ Befehlsreferenz

```bash
jobradar --setup                  # Einrichtungsassistent
jobradar                          # Vollständige Pipeline
jobradar --update                 # Inkrementell (nur neue Stellen)
jobradar --mode quick             # Schnelltest
jobradar --install-agent          # Täglichen Cron-Job einrichten

# Gesprächsbefehle (für KI-Agenten)
jobradar --show-digest            # Heutigen Digest anzeigen
jobradar --generate-app "AMD"     # Anschreiben für AMD erstellen
jobradar --mark-applied "SAP"     # SAP-Stelle als beworben markieren
jobradar --explain "Databricks"   # Score-Analyse anzeigen
jobradar --feedback "AMD liked"   # Präferenz für künftige Bewertung
```

---

## 📄 Lizenz

GNU General Public License v3.0 — siehe [LICENSE](LICENSE)

---

<div align="center">
Mit ❤️ für Jobsuchende auf dem deutschen und chinesischen Tech-Markt
</div>
