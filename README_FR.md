<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### Fini les candidatures à l'aveugle. Laisse l'IA trouver les bons postes pour toi.

[![GitHub Stars](https://img.shields.io/github/stars/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/network)
[![GitHub Issues](https://img.shields.io/github/issues/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/issues)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*Un skill [OpenClaw](https://openclaw.ai) — exécutable en autonomie ou intégré dans tout agent IA*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** lit ton CV, explore en parallèle **7 plateformes d'emploi** en Allemagne et en Chine, évalue chaque offre sur 6 axes, génère des lettres de motivation et sections de CV personnalisées, et peut **postuler automatiquement** sur BOSS直聘 et LinkedIn.

---

<div align="center">

| 💬 Communauté & Feedback | ☕ Soutenir le projet |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| Suivre sur WeChat · Envoyer des retours | WeChat Pay · Alipay — ou simplement ⭐ |

</div>

---

## ⚡ Zéro configuration avec OpenClaw — 1 message. C'est tout.

**Étape 1 — Installer** (coller dans ton terminal ou demander à OpenClaw de le faire) :

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
```
Automatiquement : clone, crée le virtualenv, installe les dépendances, redémarre le gateway OpenClaw.

**Étape 2 — Utiliser** (dire à OpenClaw ou Claude) :
```
Trouve-moi des emplois en Allemagne. Mon CV : https://github.com/…
```

Dis simplement : *"Trouve-moi des emplois en Allemagne. Mon CV : https://github.com/…"*

`setup` → 36+ offres scrapées → scoring IA → rapport HTML publié sur GitHub Pages — **en un message, sans fichier de config**.

> 📄 Exemple en direct : [report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---

## ✨ Fonctionnalités

| Fonction | Ce que tu obtiens |
|----------|------------------|
| 🌐 **7 sources en parallèle** | Bundesagentur, Indeed, Glassdoor, Google Jobs, StepStone, XING, BOSS直聘, 拉勾网, 智联招聘 |
| 🤖 **Score de compatibilité IA** | Score 6D (0–10) avec raisonnement complet |
| 🔑 **Clé API auto-détectée** | OpenClaw auth, Claude OAuth ou variables d'environnement |
| 🔌 **Tout LLM, sans lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama |
| ✉️ **Lettres personnalisées** | Générées par entreprise et CV — pas des templates |
| 📝 **Optimisation section CV** | Réécrit ton résumé + section compétences pour chaque offre |
| 📊 **Rapport HTML + Excel** | Rapport GitHub Pages + tracker Excel code couleur |
| 🚀 **Candidature automatique** | BOSS直聘 salutation Playwright + LinkedIn Easy Apply (requiert `[apply]`) |
| 🌐 **Tableau de bord web** | UI FastAPI — parcourir offres, générer candidatures, télécharger Excel |
| ⚡ **Conception incrémentale** | Seules les nouvelles offres sont évaluées — mises à jour quotidiennes en minutes |

---

## ⚙️ Comment ça marche

```
Ton CV (Markdown / PDF / DOCX / URL)
              │
              ▼
┌──────────────────────────────────────────────────┐
│ 1  DÉCOUVRIR  CV → rôles, skills, lieux          │
├──────────────────────────────────────────────────┤
│ 2  COLLECTER  7 sources en parallèle :           │
│               Bundesagentur · Indeed · Glassdoor │
│               Google Jobs · StepStone · XING(DE) │
│               BOSS直聘 · 拉勾网 · 智联招聘(CN)   │
├──────────────────────────────────────────────────┤
│ 3  FILTRER    Dédup URL · Supprimer stages       │
├──────────────────────────────────────────────────┤
│ 4  ÉVALUER    6 axes (0–10) par offre            │
├──────────────────────────────────────────────────┤
│ 5  GÉNÉRER    ✉️  Lettre · 📝 Section CV         │
├──────────────────────────────────────────────────┤
│ 6  LIVRER     📊 HTML · 📁 Excel                 │
│               🌐 Dashboard · 🚀 Candidature auto  │
└──────────────────────────────────────────────────┘
```

---

## 🚀 Démarrage rapide

### Installation la plus rapide (une commande)
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
```

### Installation manuelle
```bash
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .
# pip install -e ".[cn]"     # sources CN
# pip install -e ".[apply]"  # candidature automatique
```

### Fournir ton CV (tous les formats acceptés)
```bash
# URL (GitHub, lien direct, n'importe quelle URL HTTPS)
jobradar init --cv https://github.com/toi/repo/blob/main/cv.md

# Fichier local (.md, .pdf, .docx, .txt)
jobradar init --cv /chemin/vers/cv.pdf

# Assistant interactif (inclut l'option coller du texte)
jobradar init
```

### Première exécution
```bash
export OPENAI_API_KEY=sk-…         # ou ARK_API_KEY, DEEPSEEK_API_KEY
jobradar health                    # vérifier connexion
jobradar run --mode quick          # ~3 min test rapide pip install -e ".[cn]"   Candidature auto: pip install -e ".[apply]"

# 2 — Clé LLM (une seule suffit)
export OPENAI_API_KEY=sk-…
# export ARK_API_KEY=…   export DEEPSEEK_API_KEY=…

# 3 — Assistant de configuration
jobradar init
# Non interactif: jobradar init --cv ./cv.md --api-key ARK_API_KEY=xxx -y

# 4 — Vérifier
jobradar health

# 5 — Lancer
jobradar run --mode quick    # ~3 min, test rapide
jobradar run                  # Exécution complète
jobradar install-agent        # Automatiser chaque jour à 8h (macOS)
```

---

## 🔌 Sources d'emploi

Toutes les sources DE sont **entièrement implémentées** (sans auth ni Playwright) :

| Source | Auth | Notes |
|--------|------|-------|
| Bundesagentur für Arbeit | aucune | API officielle DE |
| Indeed DE | aucune | via python-jobspy |
| Glassdoor DE | aucune | via python-jobspy |
| Google Jobs | aucune | via python-jobspy |
| StepStone | aucune | scraper httpx + BeautifulSoup |
| XING | aucune | scraper httpx + BeautifulSoup |
| BOSS直聘 (CN) | Cookie | `BOSSZHIPIN_COOKIES` · extra `[cn]` requis |
| 拉勾网 (CN) | aucune | API mobile → AJAX → Playwright |
| 智联招聘 (CN) | aucune | API REST → fallback Playwright |

---

## 🔌 Fournisseurs LLM

Détectés par ordre de priorité :

| Priorité | Source | Variable |
|----------|--------|----------|
| 0 | **OpenClaw auth-profiles** | automatique |
| 1 | **Claude OAuth** | automatique |
| 2 | Volcengine Ark | `ARK_API_KEY` |
| 3 | Z.AI / OpenAI / DeepSeek | variables env |
| 4 | OpenRouter | `OPENROUTER_API_KEY` |
| 5 | Ollama / LM Studio | *(local)* |

---

## 🖥️ Référence CLI

```bash
jobradar init [--cv …] [--api-key ENV=val] [-y]
jobradar health / status
jobradar run [--mode quick|dry-run|score-only] [--limit N]
jobradar report [--publish] [--min-score 7]
jobradar apply [--dry-run] [--auto] [--min-score 8]
jobradar web [--port 8080]
jobradar install-agent
```

---

## 📊 Système de scoring

| Dimension | Ce qui est évalué |
|-----------|------------------|
| **Correspondance skills** | Chevauchement du stack technologique |
| **Adéquation séniorité** | Expérience vs. niveau du poste |
| **Adéquation géographique** | Faisabilité, politique de télétravail |
| **Adéquation linguistique** | Exigences DE/EN vs. compétences réelles |
| **Visa friendly** | Probabilité de sponsorisation |
| **Potentiel de croissance** | Trajectoire entreprise, apprentissage |

---

## 🤖 Candidature automatique

Requiert : `pip install -e ".[apply]" && playwright install chromium`

**BOSS直聘** : ouvre la page, vérifie l'activité RH (>7 jours inactif → passer), clique 立即沟通, envoie message de salutation personnalisable. Délai aléatoire 3–8 s, limite 50/jour.

**LinkedIn Easy Apply** : clique Easy Apply, soumet les candidatures en un seul étape (multi-étapes ignorées). Délai 4–10 s, limite 25/jour.

```bash
jobradar apply --dry-run            # prévisualiser d'abord
jobradar apply --auto --min-score 8 # puis postuler en live
```

---

## 🗺️ Feuille de route

- [x] 7 sources parallèles · Scoring IA 6D · Lettres + optimisation CV
- [x] StepStone & XING — scrapers complets
- [x] Candidature auto BOSS直聘 + LinkedIn Easy Apply
- [x] Rapport HTML + GitHub Pages · Excel · Tableau de bord web
- [x] Zéro config OpenClaw
- [ ] 前程无忧 (51job) · Digest Telegram/email · Docker · Serveur MCP

---

## ⚠️ Avertissement

Uniquement pour **recherche d'emploi personnelle, apprentissage et recherche académique**. Respecte le `robots.txt` et les conditions de chaque plateforme.

---

## 📄 Licence

GNU General Public License v3.0 — voir [LICENSE](LICENSE)

---

<div align="center">

Fait avec ❤️ pour les chercheurs d'emploi sur les marchés tech allemand et chinois

**⭐ Si JobRadar t'a aidé à décrocher des entretiens, une étoile compte énormément.**

</div>
