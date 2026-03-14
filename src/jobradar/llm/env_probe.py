"""LLM environment probe — auto-detect API keys from host frameworks.

Priority:
  1. config.yaml explicit key (already set)
  2. OpenClaw / Opencode framework env vars
  3. Claude Code / Anthropic
  4. Generic cloud providers (Z.AI, OpenAI, DeepSeek, OpenRouter, Volcengine)
  5. LM Studio local server
  6. Ollama local server
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_PROBE_TABLE = [
    # (label, key_env, base_url_env, model_env, default_base_url, default_model, provider_tag)
    ("OpenClaw",
     "OPENCLAW_API_KEY", "OPENCLAW_BASE_URL", "OPENCLAW_MODEL",
     None, None, "openclaw"),
    ("Opencode",
     "OPENCODE_API_KEY", "OPENCODE_BASE_URL", "OPENCODE_MODEL",
     None, None, "opencode"),
    ("Claude Code / Anthropic",
     "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
     "https://api.anthropic.com/v1", "claude-sonnet-4-20250514", "anthropic"),
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
    provider: str
    api_key: str
    base_url: str
    model: str
    source: str
    api_key_env: str


def probe_llm_env(config_endpoint=None) -> tuple[DetectedEndpoint | None, str]:
    # 1. config.yaml explicit key
    if config_endpoint:
        key = os.getenv(config_endpoint.api_key_env, "").strip()
        if key and key not in ("your-key-here", "REPLACE_ME"):
            return DetectedEndpoint(
                provider=config_endpoint.provider,
                api_key=key,
                base_url=config_endpoint.base_url,
                model=config_endpoint.model,
                source=f"config.yaml ({config_endpoint.provider})",
                api_key_env=config_endpoint.api_key_env,
            ), f"config.yaml ({config_endpoint.provider})"

    # 2. Env-var table
    for label, key_env, base_url_env, model_env, dflt_url, dflt_model, tag in _PROBE_TABLE:
        api_key = os.getenv(key_env, "").strip()
        if not api_key:
            continue
        base_url = os.getenv(base_url_env, "").strip() or dflt_url
        model = os.getenv(model_env, "").strip() or dflt_model
        if not base_url or not model:
            continue
        return DetectedEndpoint(
            provider=tag, api_key=api_key, base_url=base_url, model=model,
            source=f"{label} env", api_key_env=key_env,
        ), f"{label} ({key_env})"

    # 3. Local servers
    for checker in (check_lm_studio_available, check_ollama_available):
        ep = checker()
        if ep:
            return ep, ep.source

    keys = [row[1] for row in _PROBE_TABLE]
    return None, "No LLM found. Checked: " + ", ".join(keys)


def apply_env_override(config, silent: bool = False) -> tuple[bool, str]:
    """Probe and mutate config.llm.text in-place if a better endpoint is found."""
    from ..config import LLMEndpoint

    endpoint, source = probe_llm_env(config.llm.text)
    if endpoint is None:
        return False, source

    config.llm.text = LLMEndpoint(
        provider=endpoint.provider,
        model=endpoint.model,
        base_url=endpoint.base_url,
        api_key_env=endpoint.api_key_env,
        temperature=config.llm.text.temperature,
        max_tokens=config.llm.text.max_tokens,
        rate_limit_delay=config.llm.text.rate_limit_delay,
    )
    if not silent:
        logger.info("LLM: %s → %s", source, endpoint.model)
    return True, source


def check_lm_studio_available() -> DetectedEndpoint | None:
    import json, urllib.request
    base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1").rstrip("/")
    model = os.getenv("LM_STUDIO_MODEL", "").strip()
    try:
        with urllib.request.urlopen(f"{base_url}/models", timeout=2) as r:
            if not model:
                items = json.loads(r.read()).get("data", [])
                model = items[0].get("id", "") if items else "lm-studio-loaded-model"
    except Exception:
        return None
    return DetectedEndpoint(
        provider="lm_studio", api_key="lm-studio", base_url=base_url,
        model=model or "lm-studio-loaded-model", source="LM Studio (local)", api_key_env="",
    )


def check_ollama_available() -> DetectedEndpoint | None:
    import urllib.request
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.1")
    try:
        urllib.request.urlopen(base_url.replace("/v1", "") + "/api/tags", timeout=2)
    except Exception:
        return None
    return DetectedEndpoint(
        provider="ollama", api_key="no-key", base_url=base_url,
        model=model, source="Ollama (local)", api_key_env="",
    )
