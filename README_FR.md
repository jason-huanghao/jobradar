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

> **JobRadar** lit ton CV, explore en parallèle 7 plateformes d'emploi en Allemagne et en Chine, évalue chaque offre sur 6 axes grâce à un LLM, et génère automatiquement un résumé quotidien, un rapport HTML et des lettres de motivation personnalisées — entièrement automatisé.

---

<div align="center">

| 💬 Communauté & Feedback | ☕ Soutenir le projet |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| Suivre sur WeChat · Envoyer des retours | WeChat Pay · Alipay — ou simplement ⭐ |

</div>

---

## ⚡ Zéro configuration avec OpenClaw — 1 message. C'est tout.

Si tu utilises [OpenClaw](https://openclaw.ai), JobRadar s'installe comme skill et **n'a besoin que de ton CV**. La clé API est auto-détectée depuis ton environnement OpenClaw — aucun fichier de config à modifier.

```bash
# Installation du skill (une seule fois)
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && python3 -m venv .venv && .venv/bin/pip install -e . -q
openclaw gateway restart
```

Puis dis simplement :

```
Trouve-moi des emplois en Allemagne. Mon CV : https://github.com/toi/repo/blob/main/cv.md
```

L'agent appelle `setup` (clé API auto-détectée), collecte 36+ offres, les score par IA et publie un rapport HTML sur GitHub Pages — **en deux échanges, zéro fichier de config**.

> 📄 Exemple en direct : [report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---

## 📋 Navigation

| [✨ Fonctionnalités](#-fonctionnalités) | [⚙️ Comment ça marche](#️-comment-ça-marche) | [🚀 Démarrage rapide](#-démarrage-rapide) |
|:---:|:---:|:---:|
| [🤖 OpenClaw & Claude](#-avec-openclaw--claude) | [🔌 Sources d'emploi](#-sources-demploi) | [🔌 Fournisseurs LLM](#-fournisseurs-llm) |
| [⚙️ Configuration](#️-configuration) | [🖥️ Référence CLI](#️-référence-cli) | [📊 Système de scoring](#-système-de-scoring) |
| [🗺️ Feuille de route](#️-feuille-de-route) | [🤝 Contribuer](#-contribuer) | [⚠️ Avertissement](#️-avertissement) |

---

## ✨ Fonctionnalités

| Fonction | Ce que tu obtiens |
|----------|------------------|
| 🌐 **7 sources en parallèle** | Bundesagentur, Indeed, Glassdoor, Google Jobs, StepStone, BOSS直聘, 拉勾网, 智联招聘 — tout simultanément |
| 🤖 **Score de compatibilité IA** | Score 6D (0–10) avec raisonnement complet — tu sais *pourquoi* une offre est bien notée |
| 🔑 **Clé API auto-détectée** | OpenClaw auth, Claude OAuth ou variables d'env — plus jamais à saisir manuellement |
| 🔌 **Tout LLM, sans lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama |
| 📊 **Rapport HTML + Excel** | Tracker code couleur + rapport GitHub Pages en une commande |
| 📰 **Résumé quotidien** | Meilleurs matches en Markdown, pour ton téléphone ou ta boîte mail |
| ✉️ **Lettres personnalisées** | Générées par entreprise et CV — pas des templates |
| ⚡ **Conception incrémentale** | Seules les nouvelles offres sont évaluées — mises à jour en quelques minutes |
| 🧠 **Apprend tes préférences** | `--feedback "AMD liked"` — affine automatiquement le scoring futur |

---

## ⚙️ Comment ça marche

```
Ton CV (Markdown / PDF / DOCX / URL)
              │
              ▼
┌──────────────────────────────────────────────────┐
│ 1  DÉCOUVRIR  LLM parse le CV → rôles, skills,  │
│               lieux → requêtes par plateforme    │
├──────────────────────────────────────────────────┤
│ 2  COLLECTER  7 sources en threads parallèles    │
│               Bundesagentur · Indeed · Glassdoor │
│               Google Jobs · StepStone            │
│               BOSS直聘 · 拉勾网 · 智联招聘        │
├──────────────────────────────────────────────────┤
│ 3  FILTRER    Dédup par URL · Supprimer stages   │
├──────────────────────────────────────────────────┤
│ 4  ÉVALUER    LLM note chaque offre (0–10) :     │
│               Compétences · Niveau · Lieu ·      │
│               Langue · Visa · Évolution          │
├──────────────────────────────────────────────────┤
│ 5  LIVRER     📊 Rapport HTML (GitHub Pages)     │
│               📰 Digest quotidien                │
│               ✉️  Lettre de motivation           │
│               📧 Alerte e-mail                   │
└──────────────────────────────────────────────────┘
```

---

## 🚀 Démarrage rapide

```bash
# 1 — Cloner & installer
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — Définir une clé LLM (une seule suffit)
export OPENAI_API_KEY=sk-…
# export DEEPSEEK_API_KEY=…         # option la plus économique
# export ARK_API_KEY=…              # Volcengine Ark

# 3 — Configuration (génère config.yaml automatiquement)
jobradar --init --cv ./cv/cv_current.md --locations "Berlin,Hamburg,Remote"

# 4 — Vérifier la connexion
jobradar --health

# 5 — Première exécution
jobradar --mode quick               # ~3 min, 2 sources — pour tester
jobradar --update                   # exécution incrémentale complète
jobradar --install-agent            # automatiser tous les jours à 8h
```

---

## 🤖 Avec OpenClaw & Claude

**La clé API est détectée automatiquement** — l'agent n'a besoin que de l'URL de ton CV.

| Tu dis | Ce qui s'exécute |
|--------|----------------|
| « Trouve des emplois en DE. Mon CV : https://… » | `setup` + `run_pipeline` + `list_jobs` |
| « JobRadar est prêt ? » | `--health --json` |
| « Montre les meilleurs emplois du jour » | `--show-digest --json` |
| « Lettre de motivation pour SAP » | `--generate-app "SAP"` |
| « J'ai postulé chez Zalando » | `--mark-applied "Zalando"` |
| « Pourquoi Databricks a un score bas ? » | `--explain "Databricks"` |
| « Publier mon rapport d'emplois » | `get_report --publish` → URL GitHub Pages |

---

## 🔌 Sources d'emploi

| Source | Statut | Authentification |
|--------|--------|-----------------|
| Bundesagentur für Arbeit | ✅ Actif | Aucune |
| Indeed DE | ✅ Actif | Aucune |
| Glassdoor DE | ✅ Actif | Aucune |
| Google Jobs | ✅ Actif | Aucune |
| StepStone | 🔧 En développement | — |
| XING | 🔧 En développement | Token Apify |
| BOSS直聘 (CN) | ✅ Actif | Cookie + IP Chine |
| 拉勾网 (CN) | ✅ Actif | Session Cookie (auto) |
| 智联招聘 (CN) | ✅ Actif | Sans connexion |

---

## 🔌 Fournisseurs LLM

| Priorité | Source | Variable d'environnement |
|----------|--------|------------------------|
| 0 | **OpenClaw auth-profiles** | automatique |
| 1 | **Claude OAuth** | automatique |
| 2 | Volcengine Ark | `ARK_API_KEY` |
| 3 | Z.AI | `ZAI_API_KEY` |
| 4 | OpenAI | `OPENAI_API_KEY` |
| 5 | DeepSeek | `DEEPSEEK_API_KEY` |
| 6 | OpenRouter | `OPENROUTER_API_KEY` |
| 7 | Ollama | *(local)* |

---

## ⚙️ Configuration

```yaml
candidate:
  cv: "./cv/cv_current.md"
search:
  locations: ["Berlin", "Hamburg", "Remote"]
  exclude_keywords: ["Praktikum", "internship", "stage"]
scoring:
  min_score_digest: 6
  min_score_application: 7
server:
  db_path: ./jobradar.db
```

---

## 🖥️ Référence CLI

```bash
jobradar --init [--cv …] [--locations …]    # configuration initiale
jobradar --health [--json]                  # vérifier la connexion
jobradar --update                           # exécution quotidienne
jobradar --mode quick                       # test rapide (~3 min)
jobradar --show-digest [--json]             # meilleurs emplois du jour
jobradar --generate-app "Entreprise"        # lettre de motivation
jobradar --mark-applied "Entreprise"        # marquer comme postulé
jobradar --explain "Entreprise"             # analyse du score
jobradar --feedback "AMD liked"             # enregistrer une préférence
jobradar --install-agent                    # automatisation quotidienne
```

---

## 📊 Système de scoring

| Dimension | Ce qui est évalué |
|-----------|------------------|
| **Correspondance de compétences** | Chevauchement des technologies |
| **Adéquation de séniorité** | Années d'expérience vs. niveau du poste |
| **Adéquation géographique** | Faisabilité du trajet, télétravail |
| **Adéquation linguistique** | Exigences DE/EN vs. tes compétences réelles |
| **Visa friendly** | Probabilité de sponsorisation du permis de travail |
| **Potentiel de croissance** | Trajectoire de l'entreprise, opportunités d'apprentissage |

---

## 🗺️ Feuille de route

- [x] Crawling parallèle · `--health` / `--status` / `--json`
- [x] Zéro config OpenClaw (détection automatique de clé API)
- [x] Rapport HTML + publication GitHub Pages
- [ ] StepStone / XING / LinkedIn implémentation complète
- [ ] Docker · Intégration OpenClaw Cron

---

## 🤝 Contribuer

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ && pytest tests/ -v
```

---

## ⚠️ Avertissement

Ce projet est destiné **uniquement à la recherche d'emploi personnelle, à l'apprentissage technique et à la recherche académique**. Respecte le `robots.txt` et les conditions d'utilisation de chaque plateforme.

---

## 📄 Licence

GNU General Public License v3.0 — voir [LICENSE](LICENSE)

---

<div align="center">

Fait avec ❤️ pour les chercheurs d'emploi sur les marchés tech allemand et chinois

**⭐ Si JobRadar t'a aidé à décrocher des entretiens, une étoile compte énormément.**

</div>
