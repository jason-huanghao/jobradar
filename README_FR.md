<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="120" alt="JobRadar Logo" />

# JobRadar

**Agent de recherche d'emploi IA pour les postes tech en Allemagne et en Chine**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg)](https://openclaw.ai)

*Un skill [OpenClaw](https://openclaw.ai) — exécutable en autonomie ou intégré dans tout agent IA*

</div>

---

## 🌍 Langues

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

---

## Qu'est-ce que c'est ?

JobRadar lit votre CV, explore simultanément des plateformes d'emploi en Europe et en Chine, évalue chaque offre sur 6 axes grâce à un LLM et génère automatiquement un résumé quotidien, un tracker Excel et des lettres de motivation personnalisées.

```
Votre CV (Markdown)
    │
    ▼
┌──────────────────────────────────────────────────┐
│  1. DÉCOUVRIR   Parser le CV → rôles cibles      │
│                 Générer les requêtes             │
├──────────────────────────────────────────────────┤
│  2. COLLECTER   Bundesagentur · Indeed · Glass-  │
│                 door · StepStone · BOSS直聘 ·    │
│                 拉勾网 · 智联招聘 (7 sources)    │
├──────────────────────────────────────────────────┤
│  3. ÉVALUER     LLM note chaque offre (0–10) :  │
│                 Compétences · Niveau · Lieu ·   │
│                 Langue · Visa · Évolution        │
├──────────────────────────────────────────────────┤
│  4. LIVRER      Excel · Résumé quotidien ·       │
│                 Lettres de motivation · Email    │
└──────────────────────────────────────────────────┘
```

---

## ✨ Fonctionnalités

| Fonctionnalité | Détail |
|----------------|--------|
| **7 sources d'emploi** | Bundesagentur, Indeed, Glassdoor, StepStone, BOSS直聘, 拉勾网, 智联招聘 |
| **Scoring LLM** | Score 6D (0–10) avec raisonnement |
| **N'importe quel LLM** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama |
| **Tracker Excel** | Coloré par score, statut de candidature |
| **Résumé quotidien** | Synthèse Markdown des meilleures offres |
| **Lettres personnalisées** | Auto-générées par entreprise |
| **Alerte email** | Digest SMTP (Gmail compatible) |
| **Incrémental** | Seules les nouvelles offres sont évaluées |
| **Boucle de feedback** | `--feedback "AMD liked"` ajuste les futurs scores |

---

## 🚀 Démarrage rapide

```bash
# 1. Installation
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e .

# 2. Configurer une clé LLM (au choix)
export ARK_API_KEY=votre_cle         # Volcengine Ark
# export OPENAI_API_KEY=sk-…         # OpenAI
# export DEEPSEEK_API_KEY=…          # DeepSeek

# 3. Lancer l'assistant de configuration
jobradar --setup

# 4. Déposer votre CV dans cv/cv_current.md puis :
jobradar --mode quick               # Test rapide (~3 min)
jobradar                            # Pipeline complet
jobradar --install-agent            # Automatiser à 8h chaque jour
```

---

## 🖥️ Référence CLI

```bash
jobradar --setup                  # Assistant de configuration
jobradar                          # Pipeline complet
jobradar --update                 # Mise à jour incrémentale
jobradar --mode quick             # Test rapide
jobradar --install-agent          # Planifier la tâche quotidienne

# Commandes conversationnelles (pour agents IA)
jobradar --show-digest            # Afficher le résumé du jour
jobradar --generate-app "AMD"     # Lettre de motivation pour AMD
jobradar --mark-applied "SAP"     # Marquer SAP comme postulé
jobradar --explain "Databricks"   # Afficher le détail du score
jobradar --feedback "AMD liked"   # Enregistrer une préférence
```

---

## 📄 Licence

GNU General Public License v3.0 — voir [LICENSE](LICENSE)

---

<div align="center">
Fait avec ❤️ pour les chercheurs d'emploi sur les marchés tech allemand et chinois
</div>
