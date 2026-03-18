<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### Deja de enviar CVs a ciegas. Deja que la IA encuentre los empleos adecuados para ti.

[![GitHub Stars](https://img.shields.io/github/stars/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/network)
[![GitHub Issues](https://img.shields.io/github/issues/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/issues)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*Un skill de [OpenClaw](https://openclaw.ai) — ejecutable de forma autónoma o integrado en cualquier agente IA*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** lee tu CV, busca en paralelo en 7 portales de empleo en Alemania y China, usa un LLM para puntuar cada oferta en 6 dimensiones y genera automáticamente un resumen diario, un informe HTML y cartas de presentación personalizadas — completamente automatizado.

---

<div align="center">

| 💬 Comunidad y feedback | ☕ Apoya el proyecto |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| Síguenos en WeChat · Envía feedback | WeChat Pay · Alipay — o simplemente da ⭐ |

</div>

---

## ⚡ Cero configuración con OpenClaw — 1 mensaje. Listo.

Si usas [OpenClaw](https://openclaw.ai), JobRadar se instala como skill y **solo necesita tu CV**. La clave API se detecta automáticamente desde tu entorno OpenClaw.

```bash
# Instalación del skill (una sola vez)
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && python3 -m venv .venv && .venv/bin/pip install -e . -q
openclaw gateway restart
```

Luego di simplemente:

```
Busca empleos en Alemania. Mi CV: https://github.com/tú/repo/blob/main/cv.md
```

El agente ejecuta `setup` (clave API detectada automáticamente), extrae 36+ empleos, los puntúa con IA y publica un informe HTML en GitHub Pages — **en dos turnos, sin tocar ficheros de configuración**.

> 📄 Ejemplo en vivo: [report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---

## 📋 Navegación

| [✨ Características](#-características) | [⚙️ Cómo funciona](#️-cómo-funciona) | [🚀 Inicio rápido](#-inicio-rápido) |
|:---:|:---:|:---:|
| [🤖 OpenClaw & Claude](#-con-openclaw--claude) | [🔌 Fuentes de empleo](#-fuentes-de-empleo) | [🔌 Proveedores LLM](#-proveedores-llm) |
| [⚙️ Configuración](#️-configuración) | [🖥️ Referencia CLI](#️-referencia-cli) | [📊 Sistema de puntuación](#-sistema-de-puntuación) |
| [🗺️ Hoja de ruta](#️-hoja-de-ruta) | [🤝 Contribuir](#-contribuir) | [⚠️ Aviso legal](#️-aviso-legal) |

---

## ✨ Características

| Función | Qué obtienes |
|---------|-------------|
| 🌐 **7 fuentes en paralelo** | Bundesagentur, Indeed, Glassdoor, Google Jobs, StepStone, BOSS直聘, 拉勾网, 智联招聘 — todo a la vez |
| 🤖 **Puntuación IA** | Score 6D (0–10) con razonamiento completo — sabes *por qué* una oferta puntúa alto |
| 🔑 **Detección automática de API** | OpenClaw auth, Claude OAuth o variables de entorno — nunca más escribir una clave |
| 🔌 **Cualquier LLM, sin lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama |
| 📊 **Informe HTML + Excel** | Tracker con código de colores + informe GitHub Pages con un comando |
| 📰 **Resumen diario** | Mejores matches en Markdown, para móvil o correo |
| ✉️ **Cartas personalizadas** | Generadas por empresa y CV — no son plantillas |
| ⚡ **Diseño incremental** | Solo puntúa ofertas nuevas — actualizaciones diarias en minutos |
| 🧠 **Aprende tus preferencias** | `--feedback "AMD liked"` — ajusta el scoring futuro automáticamente |

---

## ⚙️ Cómo funciona

```
Tu CV (Markdown / PDF / DOCX / URL)
              │
              ▼
┌──────────────────────────────────────────────────┐
│ 1  DESCUBRIR  LLM parsea CV → roles, skills,     │
│               ubicaciones → consultas por plat.  │
├──────────────────────────────────────────────────┤
│ 2  RASTREAR   7 fuentes en hilos paralelos       │
│               Bundesagentur · Indeed · Glassdoor │
│               Google Jobs · StepStone            │
│               BOSS直聘 · 拉勾网 · 智联招聘        │
├──────────────────────────────────────────────────┤
│ 3  FILTRAR    Dedup por URL · Eliminar prácticas │
├──────────────────────────────────────────────────┤
│ 4  PUNTUAR    LLM evalúa cada oferta (0–10):     │
│               Skills · Nivel · Lugar ·           │
│               Idioma · Visado · Crecimiento      │
├──────────────────────────────────────────────────┤
│ 5  ENTREGAR   📊 Informe HTML (GitHub Pages)     │
│               📰 Digest diario                   │
│               ✉️  Carta de presentación          │
│               📧 Alerta por correo               │
└──────────────────────────────────────────────────┘
```

---

## 🚀 Inicio rápido

```bash
# 1 — Clonar e instalar
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — Configurar clave LLM (solo una)
export OPENAI_API_KEY=sk-…
# export DEEPSEEK_API_KEY=…         # opción más económica
# export ARK_API_KEY=…              # Volcengine Ark

# 3 — Configurar (genera config.yaml automáticamente)
jobradar --init --cv ./cv/cv_current.md --locations "Berlin,Hamburg,Remote"

# 4 — Verificar conexión
jobradar --health

# 5 — Primera ejecución
jobradar --mode quick               # ~3 min, 2 fuentes — para pruebas
jobradar --update                   # ejecución incremental completa
jobradar --install-agent            # automatizar cada día a las 8am
```

---

## 🤖 Con OpenClaw & Claude

**La clave API se detecta automáticamente** — el agente solo necesita la URL de tu CV.

| Dices | Se ejecuta |
|-------|-----------|
| "Busca empleos en DE. Mi CV: https://…" | `setup` + `run_pipeline` + `list_jobs` |
| "¿Está listo JobRadar?" | `--health --json` |
| "Muéstrame los mejores empleos de hoy" | `--show-digest --json` |
| "Carta de presentación para SAP" | `--generate-app "SAP"` |
| "Me he postulado en Zalando" | `--mark-applied "Zalando"` |
| "¿Por qué Databricks tiene baja puntuación?" | `--explain "Databricks"` |
| "Publicar mi informe de empleos" | `get_report --publish` → URL GitHub Pages |

---

## 🔌 Fuentes de empleo

| Fuente | Estado | Autenticación |
|--------|--------|---------------|
| Bundesagentur für Arbeit | ✅ Activo | Ninguna |
| Indeed DE | ✅ Activo | Ninguna |
| Glassdoor DE | ✅ Activo | Ninguna |
| Google Jobs | ✅ Activo | Ninguna |
| StepStone | 🔧 En desarrollo | — |
| XING | 🔧 En desarrollo | Token Apify |
| BOSS直聘 (CN) | ✅ Activo | Cookie + IP China |
| 拉勾网 (CN) | ✅ Activo | Session Cookie (auto) |
| 智联招聘 (CN) | ✅ Activo | Sin login |

---

## 🔌 Proveedores LLM

| Prioridad | Fuente | Variable de entorno |
|-----------|--------|---------------------|
| 0 | **OpenClaw auth-profiles** | automático |
| 1 | **Claude OAuth** | automático |
| 2 | Volcengine Ark | `ARK_API_KEY` |
| 3 | Z.AI | `ZAI_API_KEY` |
| 4 | OpenAI | `OPENAI_API_KEY` |
| 5 | DeepSeek | `DEEPSEEK_API_KEY` |
| 6 | OpenRouter | `OPENROUTER_API_KEY` |
| 7 | Ollama | *(local)* |

---

## ⚙️ Configuración

```yaml
candidate:
  cv: "./cv/cv_current.md"
search:
  locations: ["Berlin", "Hamburg", "Remote"]
  exclude_keywords: ["Praktikum", "internship", "prácticas"]
scoring:
  min_score_digest: 6
  min_score_application: 7
server:
  db_path: ./jobradar.db
```

---

## 🖥️ Referencia CLI

```bash
jobradar --init [--cv …] [--locations …]    # configuración inicial
jobradar --health [--json]                  # verificar conexión
jobradar --update                           # ejecución diaria (solo nuevas)
jobradar --mode quick                       # test rápido (~3 min)
jobradar --show-digest [--json]             # mejores empleos de hoy
jobradar --generate-app "Empresa"           # carta de presentación
jobradar --mark-applied "Empresa"           # marcar como postulado
jobradar --explain "Empresa"                # desglose de puntuación
jobradar --feedback "AMD liked"             # registrar preferencia
jobradar --install-agent                    # automatización diaria
```

---

## 📊 Sistema de puntuación

| Dimensión | Qué mide |
|-----------|---------|
| **Coincidencia de skills** | Superposición del stack tecnológico |
| **Adecuación de seniority** | Años de experiencia vs. nivel del rol |
| **Adecuación de ubicación** | Viabilidad del desplazamiento, política de teletrabajo |
| **Adecuación de idioma** | Requisitos DE/EN vs. tus competencias reales |
| **Visa friendly** | Probabilidad de patrocinio de permiso de trabajo |
| **Potencial de crecimiento** | Trayectoria de la empresa, oportunidades de aprendizaje |

---

## 🗺️ Hoja de ruta

- [x] Crawling paralelo · `--health` / `--status` / `--json`
- [x] Configuración cero con OpenClaw (detección automática de API)
- [x] Informe HTML + publicación GitHub Pages
- [ ] StepStone / XING / LinkedIn implementación completa
- [ ] Docker · Integración OpenClaw Cron

---

## 🤝 Contribuir

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ && pytest tests/ -v
```

---

## ⚠️ Aviso legal

Este proyecto es solo para **búsqueda de empleo personal, aprendizaje técnico e investigación académica**. Cumple con el `robots.txt` y los Términos de Servicio de cada plataforma.

---

## 📄 Licencia

GNU General Public License v3.0 — ver [LICENSE](LICENSE)

---

<div align="center">

Hecho con ❤️ para quienes buscan trabajo en los mercados tecnológicos de Alemania y China

**⭐ Si JobRadar te ayudó a conseguir entrevistas, una estrella significa mucho.**

</div>
