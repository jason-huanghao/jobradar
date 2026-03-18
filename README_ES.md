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

> **JobRadar** lee tu CV, busca en paralelo en **7 portales de empleo** en Alemania y China, puntúa cada oferta en 6 dimensiones, genera cartas de presentación y secciones de CV personalizadas, y puede **postularse automáticamente** en BOSS直聘 y LinkedIn.

---

<div align="center">

| 💬 Comunidad y feedback | ☕ Apoya el proyecto |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| Síguenos en WeChat · Envía feedback | WeChat Pay · Alipay — o simplemente da ⭐ |

</div>

---

## ⚡ Cero configuración con OpenClaw — 1 mensaje. Listo.

Instala una vez, **solo comparte tu CV** — la clave API se detecta automáticamente.

```bash
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && python3 -m venv .venv && .venv/bin/pip install -e . -q
openclaw gateway restart
```

Di simplemente: *"Busca empleos en Alemania. Mi CV: https://github.com/…"*

`setup` → 36+ empleos scrapeados → puntuación IA → informe HTML en GitHub Pages — **en un mensaje, sin archivos de configuración**.

> 📄 Ejemplo en vivo: [report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---

## ✨ Características

| Función | Qué obtienes |
|---------|-------------|
| 🌐 **7 fuentes en paralelo** | Bundesagentur, Indeed, Glassdoor, Google Jobs, StepStone, XING, BOSS直聘, 拉勾网, 智联招聘 |
| 🤖 **Puntuación IA** | Score 6D (0–10) con razonamiento completo |
| 🔑 **Detección automática de API** | OpenClaw auth, Claude OAuth o variables de entorno |
| 🔌 **Cualquier LLM, sin lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama |
| ✉️ **Cartas personalizadas** | Generadas por empresa y CV — no son plantillas |
| 📝 **Optimización de sección CV** | Reescribe tu resumen y sección de skills para cada oferta |
| 📊 **Informe HTML + Excel** | Informe GitHub Pages + tracker Excel codificado por colores |
| 🚀 **Postulación automática** | BOSS直聘 saludo Playwright + LinkedIn Easy Apply (requiere `[apply]`) |
| 🌐 **Panel web** | UI FastAPI — explorar ofertas, generar solicitudes, descargar Excel |
| ⚡ **Diseño incremental** | Solo puntúa ofertas nuevas — actualizaciones diarias en minutos |

---

## ⚙️ Cómo funciona

```
Tu CV (Markdown / PDF / DOCX / URL)
              │
              ▼
┌──────────────────────────────────────────────────┐
│ 1  DESCUBRIR  CV → roles, skills, ubicaciones    │
├──────────────────────────────────────────────────┤
│ 2  RASTREAR   7 fuentes en paralelo:             │
│               Bundesagentur · Indeed · Glassdoor │
│               Google Jobs · StepStone · XING(DE) │
│               BOSS直聘 · 拉勾网 · 智联招聘(CN)   │
├──────────────────────────────────────────────────┤
│ 3  FILTRAR    Dedup URL · Eliminar prácticas     │
├──────────────────────────────────────────────────┤
│ 4  PUNTUAR    6 dimensiones (0–10) por oferta    │
├──────────────────────────────────────────────────┤
│ 5  GENERAR    ✉️  Carta · 📝 Sección CV          │
├──────────────────────────────────────────────────┤
│ 6  ENTREGAR   📊 HTML · 📁 Excel                 │
│               🌐 Panel web · 🚀 Auto-postulación  │
└──────────────────────────────────────────────────┘
```

---

## 🚀 Inicio rápido

```bash
# 1 — Clonar e instalar
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .
# CN: pip install -e ".[cn]"   Auto-apply: pip install -e ".[apply]"

# 2 — Clave LLM (solo una)
export OPENAI_API_KEY=sk-…
# export ARK_API_KEY=…   export DEEPSEEK_API_KEY=…

# 3 — Asistente de configuración
jobradar init
# No interactivo: jobradar init --cv ./cv.md --api-key ARK_API_KEY=xxx -y

# 4 — Verificar
jobradar health

# 5 — Ejecutar
jobradar run --mode quick    # ~3 min, prueba rápida
jobradar run                  # Ejecución completa
jobradar install-agent        # Automatizar cada día a las 8:00 (macOS)
```

---

## 🔌 Fuentes de empleo

Todas las fuentes DE están **completamente implementadas** (sin auth ni Playwright):

| Fuente | Auth | Notas |
|--------|------|-------|
| Bundesagentur für Arbeit | ninguna | API oficial alemana |
| Indeed DE | ninguna | via python-jobspy |
| Glassdoor DE | ninguna | via python-jobspy |
| Google Jobs | ninguna | via python-jobspy |
| StepStone | ninguna | scraper httpx + BeautifulSoup |
| XING | ninguna | scraper httpx + BeautifulSoup |
| BOSS直聘 (CN) | Cookie | `BOSSZHIPIN_COOKIES` · extra `[cn]` requerido |
| 拉勾网 (CN) | ninguna | API móvil → AJAX → Playwright |
| 智联招聘 (CN) | ninguna | API REST → fallback Playwright |

---

## 🔌 Proveedores LLM

Detectados en orden de prioridad:

| Prioridad | Fuente | Variable |
|-----------|--------|----------|
| 0 | **OpenClaw auth-profiles** | automático |
| 1 | **Claude OAuth** | automático |
| 2 | Volcengine Ark | `ARK_API_KEY` |
| 3 | Z.AI / OpenAI / DeepSeek | variables env |
| 4 | OpenRouter | `OPENROUTER_API_KEY` |
| 5 | Ollama / LM Studio | *(local)* |

---

## 🖥️ Referencia CLI

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

## 📊 Sistema de puntuación

| Dimensión | Qué mide |
|-----------|---------|
| **Coincidencia skills** | Superposición del stack tecnológico |
| **Adecuación seniority** | Experiencia vs. nivel del puesto |
| **Adecuación ubicación** | Viabilidad, política de teletrabajo |
| **Adecuación idioma** | Requisitos DE/EN vs. competencias reales |
| **Visa friendly** | Probabilidad de patrocinio de permiso |
| **Potencial crecimiento** | Trayectoria empresa, aprendizaje |

---

## 🤖 Postulación automática

Requiere: `pip install -e ".[apply]" && playwright install chromium`

**BOSS直聘**: abre la página, verifica actividad HR (>7 días inactivo → omitir), hace clic en 立即沟通, envía mensaje de saludo personalizable. Retraso aleatorio 3–8 s, límite 50/día.

**LinkedIn Easy Apply**: hace clic en Easy Apply, envía solicitudes de un solo paso (omite formularios multi-paso). Retraso 4–10 s, límite 25/día.

```bash
jobradar apply --dry-run            # primero previsualizar
jobradar apply --auto --min-score 8 # luego postular en vivo
```

---

## 🗺️ Hoja de ruta

- [x] 7 fuentes paralelas · Scoring IA 6D · Cartas + optimización CV
- [x] StepStone & XING — scrapers completos
- [x] Auto-postulación BOSS直聘 + LinkedIn Easy Apply
- [x] Informe HTML + GitHub Pages · Excel · Panel web
- [x] OpenClaw cero configuración
- [ ] 前程无忧 (51job) · Digest Telegram/email · Docker · Servidor MCP

---

## ⚠️ Aviso legal

Solo para **búsqueda personal, aprendizaje y research**. Cumple el `robots.txt` y los términos de cada plataforma.

---

## 📄 Licencia

GNU General Public License v3.0 — ver [LICENSE](LICENSE)

---

<div align="center">

Hecho con ❤️ para quienes buscan trabajo en los mercados tech de Alemania y China

**⭐ Si JobRadar te ayudó a conseguir entrevistas, una estrella cuenta mucho.**

</div>
