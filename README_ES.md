<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### Deja de enviar CVs a ciegas. Deja que la IA encuentre los empleos adecuados para ti.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*Un skill de [OpenClaw](https://openclaw.ai) — ejecutable de forma autónoma o integrado en cualquier agente IA*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** lee tu CV, busca en paralelo en 7 portales de empleo en Alemania y China, usa un LLM para puntuar cada oferta en 6 dimensiones y genera automáticamente un resumen diario, un tracker Excel y cartas de presentación personalizadas. Sube tu CV, indica dónde buscar, y deja que funcione solo.

---

<div align="center">

| 💬 Comunidad y feedback | ☕ Apoya el proyecto |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="160" alt="WeChat Account" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat Pay & Alipay" /> |
| Sigue en WeChat · Envía feedback | WeChat Pay · Alipay — o simplemente da ⭐ |

</div>

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
| 🤖 **Puntuación IA de compatibilidad** | Score 6D (0–10) con razonamiento completo — sabes *por qué* una oferta puntúa alto |
| 🔌 **Cualquier LLM, sin lock-in** | Volcengine Ark, Z.AI, OpenAI, DeepSeek, OpenRouter, Ollama — autodetectado desde variables de entorno |
| 📊 **Tracker Excel** | Codificado por colores según score, estado de candidatura, fecha de publicación |
| 📰 **Resumen diario** | Mejores matches en Markdown, listo para enviar a tu móvil o correo |
| ✉️ **Cartas personalizadas** | Generadas por empresa y CV — no son plantillas |
| ⚡ **Diseño incremental** | Solo puntúa ofertas nuevas — actualizaciones diarias en minutos |
| 🧠 **Aprende tus preferencias** | `--feedback "AMD liked"` — un comando para ajustar todo el scoring futuro |

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
│               BOSS直聘 · 拉勾网 · 智联招聘        │
├──────────────────────────────────────────────────┤
│ 3  FILTRAR    Dedup por URL · Eliminar prácticas │
│               (gratuito, antes del LLM)          │
├──────────────────────────────────────────────────┤
│ 4  PUNTUAR    LLM evalúa cada oferta (0–10):     │
│               Skills · Nivel · Lugar ·           │
│               Idioma · Visado · Crecimiento      │
├──────────────────────────────────────────────────┤
│ 5  ENTREGAR   Excel · Resumen diario ·           │
│               Cartas · Alerta email              │
└──────────────────────────────────────────────────┘
```

---

## 🚀 Inicio rápido

```bash
# 1 — Clonar & instalar
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — Configurar clave LLM (una es suficiente)
export OPENAI_API_KEY=sk-…          # OpenAI
# export DEEPSEEK_API_KEY=…         # DeepSeek (más económico)
# export ARK_API_KEY=…              # Volcengine Ark

# 3 — Inicializar (genera config.yaml automáticamente)
jobradar --init --cv ./cv/cv_current.md --locations "Berlin,Hamburg,Remote"

# 4 — Verificar conexión
jobradar --health

# 5 — Primera ejecución
jobradar --mode quick               # ~3 min, 2 fuentes — para pruebas
jobradar --update                   # Ejecución incremental completa
jobradar --install-agent            # Automatizar a las 8am diarias
```

---

## 🤖 Con OpenClaw & Claude

| Tú dices | Se ejecuta |
|----------|-----------|
| «Configura JobRadar. Mi CV está en https://…» | `jobradar --init --cv … --llm … --key …` |
| «¿Está listo JobRadar?» | `jobradar --health --json` |
| «Busca empleos de IA ahora» | `jobradar --mode quick` |
| «Muéstrame los mejores empleos de hoy» | `jobradar --show-digest --json` |
| «Escribe una carta para DeepL» | `jobradar --generate-app "DeepL"` |
| «Me he postulado en SAP» | `jobradar --mark-applied "SAP"` |
| «¿Por qué Databricks tiene baja puntuación?» | `jobradar --explain "Databricks"` |

---

## 🔌 Fuentes de empleo

| Fuente | Estado | Autenticación |
|--------|--------|--------------|
| Bundesagentur für Arbeit | ✅ Activo | Ninguna |
| Indeed DE | ✅ Activo | Ninguna |
| Glassdoor DE | ✅ Activo | Ninguna |
| Google Jobs | ✅ Activo | Ninguna |
| StepStone | 🔧 En desarrollo | — |
| XING | 🔧 En desarrollo | Token Apify |
| BOSS直聘 (CN) | ✅ Activo | Cookie + IP china |
| 拉勾网 (CN) | ✅ Activo | Session Cookie (auto) |
| 智联招聘 (CN) | ✅ Activo | No requerida |

---

## 🔌 Proveedores LLM

| Proveedor | Variable de entorno | Notas |
|-----------|--------------------|----- |
| Volcengine Ark | `ARK_API_KEY` | Serie doubao |
| Z.AI | `ZAI_API_KEY` | — |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini recomendado |
| DeepSeek | `DEEPSEEK_API_KEY` | Opción más económica |
| OpenRouter | `OPENROUTER_API_KEY` | 200+ modelos |
| Ollama | *(ninguna)* | Completamente local |

---

## ⚙️ Configuración

```yaml
candidate:
  cv_path: "./cv/cv_current.md"
search:
  locations: ["Berlin", "Munich", "Remote"]
  exclude_keywords: ["Praktikum", "internship", "Ausbildung"]
  exclude_companies: ["MiAntigualEmpresa"]
scoring:
  min_score_digest: 6
  min_score_application: 7
```

---

## 🖥️ Referencia CLI

```bash
jobradar --init [--cv …] [--locations …] [--llm …] [--key …]
jobradar --health [--json]          # Verificar conexión
jobradar --status [--json]          # Estadísticas del pool
jobradar --update                   # Ejecución diaria (solo nuevas)
jobradar --mode quick               # Prueba rápida (~3 min)
jobradar --show-digest [--json]     # Mejores empleos de hoy
jobradar --generate-app "Empresa"   # Carta de presentación
jobradar --mark-applied "Empresa"   # Marcar como postulado
jobradar --explain "Empresa"        # Desglose de puntuación
jobradar --feedback "AMD liked"     # Registrar preferencia
jobradar --install-agent            # Automatización diaria
```

---

## 📊 Sistema de puntuación

| Dimensión | Qué mide |
|-----------|---------|
| **Compatibilidad técnica** | Solapamiento de stack tecnológico |
| **Adecuación de nivel** | Años de experiencia vs. nivel del rol |
| **Idoneidad de ubicación** | Distancia al trabajo, política de remoto |
| **Idoneidad lingüística** | Requisitos DE/EN vs. tu nivel real |
| **Visa favorable** | Probabilidad de patrocinio de permiso de trabajo |
| **Potencial de crecimiento** | Trayectoria profesional, relevancia del dominio |

---

## 🗺️ Hoja de ruta

- [x] Crawling paralelo (ThreadPoolExecutor)
- [x] `--status` / `--health` / `--json`
- [x] `--init` configuración no interactiva
- [x] Filtros negativos de keywords y empresas
- [ ] StepStone implementación completa
- [ ] Adaptador nativo de XING
- [ ] Docker en un solo comando

---

## 🤝 Contribuir

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ && pytest tests/ -v
```

---

## ⚠️ Aviso legal

Este proyecto está destinado **exclusivamente para búsqueda personal de empleo, aprendizaje técnico e investigación académica**. Los usuarios deben cumplir con el `robots.txt` y los Términos de Servicio de cada plataforma.

---

## 📄 Licencia

GNU General Public License v3.0 — ver [LICENSE](LICENSE)

---

<div align="center">

Hecho con ❤️ para quienes buscan trabajo en los mercados tech de Alemania y China

**⭐ Si JobRadar te ayudó a conseguir entrevistas, una estrella significa mucho.**

</div>
