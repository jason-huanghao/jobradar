"""LLM environment probe — detect API keys from host agent frameworks.

Priority order (highest → lowest):
  1. Explicit config.yaml llm.text setting (with valid key in .env)
  2. OpenClaw  → OPENCLAW_API_KEY / OPENCLAW_MODEL / OPENCLAW_BASE_URL
  3. Opencode  → OPENCODE_API_KEY / OPENCODE_MODEL / OPENCODE_BASE_URL
  4. Claude Code → ANTHROPIC_API_KEY (+ optional ANTHROPIC_BASE_URL / ANTHROPIC_MODEL)
  5. Generic fallback env vars: ZAI_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY, …
  6. LM Studio local server  (http://localhost:1234/v1, no key needed)
  7. Ollama local server     (http://localhost:11434/v1, no key needed)

If no API key / local server is found anywhere, returns (None, reason_string)
so the caller can guide the user through setup.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ── Well-known env-var probe table ─────────────────────────────────
# Each entry:
#   (framework_name, api_key_env, base_url_env, model_env,
#    default_base_url, default_model, provider_tag)
#
# If default_base_url is None, the base_url env var MUST be set explicitly.
# If default_model   is None, the model    env var MUST be set explicitly.

_PROBE_TABLE = [
    ("OpenClaw",
     "OPENCLAW_API_KEY", "OPENCLAW_BASE_URL", "OPENCLAW_MODEL",
     None, None, "openclaw"),

    ("Opencode",
     "OPENCODE_API_KEY", "OPENCODE_BASE_URL", "OPENCODE_MODEL",
     None, None, "opencode"),

    ("Claude Code / Anthropic",
     "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
     "https://api.anthropic.com/v1", "claude-sonnet-4-5-20251001", "anthropic"),

    ("Z.AI",
     "ZAI_API_KEY", "ZAI_BASE_URL", "ZAI_MODEL",
     "https://api.z.ai/v1", "claude-sonnet-4-20250514", "zai"),

    ("OpenAI",
     "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL",
     "https://api.openai.com/v1", "gpt-4o-mini", "openai"),

    ("DeepSeek",
     "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
     "https://api.deepseek.com/v1", "deepseek-chat", "deepseek"),

    ("OpenRouter",
     "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_MODEL",
     "https://openrouter.ai/api/v1", "anthropic/claude-3-5-haiku", "openrouter"),

    ("Volcengine Ark",
     "ARK_API_KEY", "ARK_BASE_URL", "ARK_MODEL",
     "https://ark.cn-beijing.volces.com/api/coding/v3", "doubao-seed-2.0-code", "volcengine"),
]


@dataclass
class DetectedEndpoint:
    """A fully-resolved LLM endpoint detected from the environment."""
    provider: str
    api_key: str
    base_url: str
    model: str
    source: str       # human-readable: "OpenClaw env", "config.yaml", …
    api_key_env: str  # env var name that held the key (empty for local servers)


def probe_llm_env(
    config_endpoint,  # LLMEndpoint from config.yaml (may be None)
) -> tuple[DetectedEndpoint | None, str]:
    """Probe environment for a usable LLM endpoint.

    Returns:
        (DetectedEndpoint, source_description)  — if found
        (None, reason)                          — if nothing usable found
    """
    # 1. config.yaml explicit key
    if config_endpoint:
        configured_key = os.getenv(config_endpoint.api_key_env, "").strip()
        if (
            configured_key
            and configured_key not in ("your-key-here", "REPLACE_ME", "")
            and config_endpoint.base_url
            and config_endpoint.model
        ):
            return (
                DetectedEndpoint(
                    provider=config_endpoint.provider,
                    api_key=configured_key,
                    base_url=config_endpoint.base_url,
                    model=config_endpoint.model,
                    source=f"config.yaml ({config_endpoint.provider})",
                    api_key_env=config_endpoint.api_key_env,
                ),
                f"config.yaml ({config_endpoint.provider})",
            )

    # 2. Cloud/remote provider env vars
    for (framework, key_env, base_url_env, model_env,
         default_base_url, default_model, provider_tag) in _PROBE_TABLE:
        api_key = os.getenv(key_env, "").strip()
        if not api_key:
            continue
        base_url = os.getenv(base_url_env, "").strip() or default_base_url
        model    = os.getenv(model_env,    "").strip() or default_model
        if not base_url:
            logger.debug("Probe: %s has key but no base_url (set %s)", framework, base_url_env)
            continue
        if not model:
            logger.debug("Probe: %s has key but no model (set %s)", framework, model_env)
            continue
        logger.info("LLM auto-detected from %s (key: %s=***)", framework, key_env)
        return (
            DetectedEndpoint(
                provider=provider_tag, api_key=api_key,
                base_url=base_url, model=model,
                source=f"{framework} environment",
                api_key_env=key_env,
            ),
            f"{framework} environment ({key_env})",
        )

    # 3. Local servers — LM Studio first, then Ollama
    lm_studio = check_lm_studio_available()
    if lm_studio:
        return lm_studio, lm_studio.source

    ollama = check_ollama_available()
    if ollama:
        return ollama, ollama.source

    # 4. Nothing found
    all_env_vars = [row[1] for row in _PROBE_TABLE]
    return None, "No LLM API key found. Checked: " + ", ".join(all_env_vars)


def apply_env_override(config, silent: bool = False) -> tuple[bool, str]:
    """Probe the environment and override config.llm.text if a better key is found.

    Mutates config.llm.text in-place.  Preserves tuning params (temperature,
    max_tokens, rate_limit_delay) from the original config.

    Returns:
        (True, source_description)  — key found and applied
        (False, reason)             — nothing usable found
    """
    from .config import LLMEndpoint

    endpoint, source = probe_llm_env(config.llm.text)
    if endpoint is None:
        return False, source

    current_key = os.getenv(config.llm.text.api_key_env, "").strip()
    already_configured = bool(current_key)

    if not already_configured or endpoint.api_key_env != config.llm.text.api_key_env:
        new_endpoint = LLMEndpoint(
            provider=endpoint.provider,
            model=endpoint.model,
            base_url=endpoint.base_url,
            api_key_env=endpoint.api_key_env,
            temperature=config.llm.text.temperature,
            max_tokens=config.llm.text.max_tokens,
            rate_limit_delay=config.llm.text.rate_limit_delay,
        )
        config.llm.text = new_endpoint
        if not silent:
            logger.info("LLM override applied: %s → %s / %s",
                        source, endpoint.model, endpoint.base_url)

    return True, source


def format_setup_guidance() -> str:
    """Return a human-readable setup guide shown when no LLM is found."""
    lines = [
        "",
        "╔══════════════════════════════════════════════════════════╗",
        "║  ⚙️   No LLM configured                                 ║",
        "╚══════════════════════════════════════════════════════════╝",
        "",
        "JobRadar needs an LLM to parse your CV and score jobs.",
        "Choose ONE of these options:",
        "",
        "  Option A — Run the interactive setup wizard (recommended):",
        "    jobradar --setup",
        "",
        "  Option B — Set an environment variable (takes effect immediately):",
        "    export ZAI_API_KEY=your-key          # Z.AI",
        "    export OPENAI_API_KEY=your-key       # OpenAI",
        "    export DEEPSEEK_API_KEY=your-key     # DeepSeek (~$0.14/1M tokens)",
        "    export ARK_API_KEY=your-key          # Volcengine Ark (doubao)",
        "    export ANTHROPIC_API_KEY=your-key    # Claude Code / Anthropic",
        "    export OPENROUTER_API_KEY=your-key   # OpenRouter (200+ models)",
        "",
        "  Option C — If running inside OpenClaw / Opencode:",
        "    Set OPENCLAW_API_KEY + OPENCLAW_BASE_URL + OPENCLAW_MODEL",
        "    (or equivalent OPENCODE_* vars) in your agent environment.",
        "    JobRadar will auto-detect them at startup.",
        "",
        "  Option D — Use a free local model (no API key, no cost):",
        "    LM Studio:  download from https://lmstudio.ai",
        "                load any model → enable Local Server → Start",
        "                (auto-detected at http://localhost:1234/v1)",
        "    Ollama:     brew install ollama && ollama pull llama3.1",
        "                (auto-detected at http://localhost:11434/v1)",
        "    Override detected model:  export LM_STUDIO_MODEL=<model-id>",
        "                              export OLLAMA_MODEL=<model-name>",
        "",
    ]
    return "\n".join(lines)


# ── Local server detection ─────────────────────────────────────────


def check_lm_studio_available() -> DetectedEndpoint | None:
    """Check if LM Studio's local server is running (default port 1234).

    LM Studio exposes an OpenAI-compatible API at http://localhost:1234/v1.
    No real API key is required — any non-empty string is accepted.

    Model resolution order:
      1. LM_STUDIO_MODEL env var   (explicit user override)
      2. First id from GET /v1/models   (currently loaded model)
      3. Fallback sentinel  "lm-studio-loaded-model"

    Custom server:  export LM_STUDIO_BASE_URL=http://192.168.1.10:1234/v1
    """
    import json
    import urllib.request

    base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1").rstrip("/")
    explicit_model = os.getenv("LM_STUDIO_MODEL", "").strip()

    try:
        with urllib.request.urlopen(f"{base_url}/models", timeout=2) as resp:
            raw = resp.read().decode("utf-8")
    except Exception:
        return None  # server not running or unreachable

    model = explicit_model
    if not model:
        try:
            items = json.loads(raw).get("data", [])
            if items:
                model = (items[0].get("id") or "").strip()
        except (json.JSONDecodeError, KeyError, IndexError, AttributeError):
            pass

    if not model:
        model = "lm-studio-loaded-model"

    logger.info("LM Studio auto-detected at %s — model: %s", base_url, model)
    return DetectedEndpoint(
        provider="lm_studio",
        api_key="lm-studio",   # LM Studio accepts any non-empty string
        base_url=base_url,
        model=model,
        source="LM Studio (local)",
        api_key_env="",
    )


def check_ollama_available() -> DetectedEndpoint | None:
    """Check if a local Ollama instance is running (default port 11434).

    Custom address:  export OLLAMA_BASE_URL=http://remote-host:11434/v1
    Custom model:    export OLLAMA_MODEL=mistral
    """
    import urllib.request

    base_url   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    model      = os.getenv("OLLAMA_MODEL", "llama3.1")
    health_url = base_url.replace("/v1", "") + "/api/tags"

    try:
        urllib.request.urlopen(health_url, timeout=2)
    except Exception:
        return None

    logger.info("Ollama auto-detected at %s — model: %s", base_url, model)
    return DetectedEndpoint(
        provider="ollama",
        api_key="no-key",
        base_url=base_url,
        model=model,
        source="Ollama (local)",
        api_key_env="",
    )
