<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="120" alt="JobRadar Logo" />

# JobRadar

**Agente de búsqueda de empleo con IA para puestos tech en Alemania y China**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg)](https://openclaw.ai)

*Un skill de [OpenClaw](https://openclaw.ai) — ejecutable de forma autónoma o integrado en cualquier agente IA*

</div>

---

## 🌍 Idiomas

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

---

## ¿Qué hace?

JobRadar lee tu CV, busca en múltiples portales de empleo en Europa y China, puntúa cada oferta con un LLM en 6 dimensiones y entrega automáticamente un resumen diario, un tracker de Excel y cartas de presentación personalizadas.

```
Tu CV (Markdown)
    │
    ▼
┌──────────────────────────────────────────────────┐
│  1. DESCUBRIR   Parsear CV → extraer roles       │
│                 Generar consultas por plataforma │
├──────────────────────────────────────────────────┤
│  2. RASTREAR    Bundesagentur · Indeed · Glass-  │
│                 door · StepStone · BOSS直聘 ·    │
│                 拉勾网 · 智联招聘 (7 fuentes)    │
├──────────────────────────────────────────────────┤
│  3. PUNTUAR     LLM evalúa cada oferta (0–10):  │
│                 Skills · Nivel · Lugar ·        │
│                 Idioma · Visado · Crecimiento   │
├──────────────────────────────────────────────────┤
│  4. ENTREGAR    Excel · Resumen diario ·         │
│                 Cartas de presentación · Email   │
└──────────────────────────────────────────────────┘
```

---

## ✨ Características

| Función | Detalle |
|---------|---------|
| **7 fuentes de empleo** | Bundesagentur, Indeed, Glassdoor, StepStone, BOSS直聘, 拉勾网, 智联招聘 |
| **Puntuación LLM** | Puntuación 6D (0–10) con razonamiento |
| **Cualquier LLM** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama |
| **Tracker Excel** | Codificado por colores, con estado de solicitud |
| **Resumen diario** | Resumen Markdown de los mejores matches |
| **Cartas personalizadas** | Auto-generadas por empresa |
| **Alerta por email** | Digest SMTP (compatible con Gmail) |
| **Incremental** | Solo puntúa ofertas nuevas — actualizaciones rápidas |
| **Bucle de feedback** | `--feedback "AMD liked"` ajusta futuras puntuaciones |

---

## 🚀 Inicio rápido

```bash
# 1. Instalación
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e .

# 2. Configurar clave LLM (elige una)
export ARK_API_KEY=tu_clave          # Volcengine Ark
# export OPENAI_API_KEY=sk-…         # OpenAI
# export DEEPSEEK_API_KEY=…          # DeepSeek

# 3. Ejecutar el asistente de configuración
jobradar --setup

# 4. Coloca tu CV en cv/cv_current.md y ejecuta:
jobradar --mode quick               # Prueba rápida (~3 min)
jobradar                            # Pipeline completo
jobradar --install-agent            # Automatizar a las 8am diarias
```

---

## 🖥️ Referencia CLI

```bash
jobradar --setup                  # Asistente de configuración
jobradar                          # Pipeline completo
jobradar --update                 # Incremental (solo nuevas ofertas)
jobradar --mode quick             # Prueba rápida
jobradar --install-agent          # Programar tarea diaria

# Comandos conversacionales (para agentes IA)
jobradar --show-digest            # Ver resumen de hoy
jobradar --generate-app "AMD"     # Carta de presentación para AMD
jobradar --mark-applied "SAP"     # Marcar SAP como solicitado
jobradar --explain "Databricks"   # Ver desglose de puntuación
jobradar --feedback "AMD liked"   # Registrar preferencia
```

---

## 📄 Licencia

GNU General Public License v3.0 — ver [LICENSE](LICENSE)

---

<div align="center">
Hecho con ❤️ para quienes buscan trabajo en los mercados tech de Alemania y China
</div>
