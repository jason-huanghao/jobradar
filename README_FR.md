<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### Fini les candidatures à l'aveugle. Laisse l'IA trouver les bons postes pour toi.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*Un skill [OpenClaw](https://openclaw.ai) — exécutable en autonomie ou intégré dans tout agent IA*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** lit ton CV, explore en parallèle 7 plateformes d'emploi en Allemagne et en Chine, évalue chaque offre sur 6 axes grâce à un LLM, et génère automatiquement un résumé quotidien, un tracker Excel et des lettres de motivation personnalisées. Dépose ton CV, dis-lui où chercher — le reste est automatique.

---

<div align="center">

| 💬 Communauté & Feedback | ☕ Soutenir le projet |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| Suivre sur WeChat · Envoyer des retours | WeChat Pay · Alipay — ou simplement ⭐ |

</div>

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
| 🔌 **Tout LLM, sans lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama — auto-détecté depuis les variables d'environnement |
| 📊 **Tracker Excel** | Code couleur par score, statut de candidature, date de publication |
| 📰 **Résumé quotidien** | Meilleurs matches en Markdown, prêt pour ton téléphone ou ta boîte mail |
| ✉️ **Lettres personnalisées** | Générées par entreprise et CV — pas des templates |
| ⚡ **Conception incrémentale** | Seules les nouvelles offres sont évaluées — mises à jour quotidiennes en quelques minutes |
| 🧠 **Apprend tes préférences** | `--feedback "AMD liked"` — une commande pour affiner tout le scoring futur |

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
│               BOSS直聘 · 拉勾网 · 智联招聘        │
├──────────────────────────────────────────────────┤
│ 3  FILTRER    Dédup par URL · Supprimer stages   │
│               (gratuit, avant le LLM)            │
├──────────────────────────────────────────────────┤
│ 4  ÉVALUER    LLM note chaque offre (0–10) :     │
│               Compétences · Niveau · Lieu ·      │
│               Langue · Visa · Évolution          │
├──────────────────────────────────────────────────┤
│ 5  LIVRER     Excel · Résumé quotidien ·         │
│               Lettres · Alerte email             │
└──────────────────────────────────────────────────┘
```

---

## 🚀 Démarrage rapide

```bash
# 1 — Cloner & installer
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — Configurer une clé LLM (une seule suffit)
export OPENAI_API_KEY=sk-…          # OpenAI
# export DEEPSEEK_API_KEY=…         # DeepSeek (le plus économique)
# export ARK_API_KEY=…              # Volcengine Ark

# 3 — Initialiser (génère config.yaml automatiquement)
jobradar --init --cv ./cv/cv_current.md --locations "Berlin,Paris,Remote"

# 4 — Vérifier la connexion
jobradar --health

# 5 — Premier lancement
jobradar --mode quick               # ~3 min, 2 sources — pour tester
jobradar --update                   # Lancement incrémental complet
jobradar --install-agent            # Automatiser à 8h chaque matin
```

---

## 🤖 Avec OpenClaw & Claude

| Tu dis | Ce qui s'exécute |
|--------|-----------------|
| «Configure JobRadar. Mon CV est à https://…» | `jobradar --init --cv … --llm … --key …` |
| «JobRadar est-il prêt ?» | `jobradar --health --json` |
| «Cherche des emplois IA maintenant» | `jobradar --mode quick` |
| «Montre-moi les meilleurs emplois du jour» | `jobradar --show-digest --json` |
| «Écris une lettre pour DeepL» | `jobradar --generate-app "DeepL"` |
| «J'ai postulé chez SAP» | `jobradar --mark-applied "SAP"` |
| «Pourquoi Databricks a un score faible ?» | `jobradar --explain "Databricks"` |

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
| BOSS直聘 (CN) | ✅ Actif | Cookie + IP chinoise |
| 拉勾网 (CN) | ✅ Actif | Session Cookie (auto) |
| 智联招聘 (CN) | ✅ Actif | Non requise |

---

## 🔌 Fournisseurs LLM

| Fournisseur | Variable d'environnement | Notes |
|-------------|------------------------|-------|
| Volcengine Ark | `ARK_API_KEY` | Série doubao |
| Z.AI | `ZAI_API_KEY` | — |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini recommandé |
| DeepSeek | `DEEPSEEK_API_KEY` | Option la plus économique |
| OpenRouter | `OPENROUTER_API_KEY` | 200+ modèles |
| Ollama | *(aucune)* | Entièrement local |

---

## ⚙️ Configuration

```yaml
candidate:
  cv_path: "./cv/cv_current.md"
search:
  locations: ["Berlin", "Hamburg", "Remote"]
  exclude_keywords: ["Praktikum", "stage", "internship"]
  exclude_companies: ["MonAncienEmployeur"]
scoring:
  min_score_digest: 6
  min_score_application: 7
```

---

## 🖥️ Référence CLI

```bash
jobradar --init [--cv …] [--locations …] [--llm …] [--key …]
jobradar --health [--json]          # Vérifier la connexion
jobradar --status [--json]          # Statistiques du pool
jobradar --update                   # Lancement quotidien (nouvelles offres)
jobradar --mode quick               # Test rapide (~3 min)
jobradar --show-digest [--json]     # Meilleures offres du jour
jobradar --generate-app "Entreprise"  # Lettre de motivation
jobradar --mark-applied "Entreprise"  # Marquer comme postulé
jobradar --explain "Entreprise"     # Détail du score
jobradar --feedback "AMD liked"    # Enregistrer une préférence
jobradar --install-agent            # Automatisation quotidienne
```

---

## 📊 Système de scoring

| Dimension | Ce qui est évalué |
|-----------|-----------------|
| **Correspondance technique** | Chevauchement du stack technologique |
| **Adéquation de niveau** | Années d'expérience vs. niveau du poste |
| **Adéquation géographique** | Trajet, politique de télétravail |
| **Adéquation linguistique** | Exigences DE/EN vs. ton niveau réel |
| **Visa favorable** | Probabilité de sponsorisation de permis |
| **Potentiel de croissance** | Trajectoire de carrière, pertinence du domaine |

---

## 🗺️ Feuille de route

- [x] Crawling parallèle (ThreadPoolExecutor)
- [x] `--status` / `--health` / `--json`
- [x] `--init` configuration non interactive
- [x] Filtres négatifs de mots-clés et d'entreprises
- [ ] Implémentation complète de StepStone
- [ ] Adaptateur natif XING
- [ ] Docker en une ligne

---

## 🤝 Contribuer

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ && pytest tests/ -v
```

---

## ⚠️ Avertissement

Ce projet est destiné **uniquement à la recherche personnelle d'emploi, l'apprentissage technique et la recherche académique**. Les utilisateurs doivent respecter le `robots.txt` et les Conditions d'utilisation de chaque plateforme.

---

## 📄 Licence

GNU General Public License v3.0 — voir [LICENSE](LICENSE)

---

<div align="center">

Fait avec ❤️ pour les chercheurs d'emploi sur les marchés tech allemand et chinois

**⭐ Si JobRadar t'a aidé à décrocher des entretiens, une étoile fait vraiment plaisir.**

</div>
