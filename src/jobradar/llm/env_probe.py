"""LLM environment probe — auto-detect API keys and OAuth tokens.

Priority order:
  0. Claude OAuth    — ~/.claude/.credentials.json (free for Claude Code subscribers)
  1. OPENCLAW_API_KEY — OpenClaw runtime key → Z.AI proxy
  2. ZAI_API_KEY / ARK_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY / etc.
  3. LM Studio local (localhost:1234)
  4. Ollama local    (localhost:11434)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_PROBE_TABLE = [
    # (display_name, env_var, base_url_env, model_env, default_base_url, default_model, provider_id)
    ("OpenClaw",      "OPENCLAW_API_KEY",   "OPENCLAW_BASE_URL",   "OPENCLAW_MODEL",
     "https://api.z.ai/v1",                             "claude-sonnet-4-20250514", "openclaw"),
    ("Z.AI",          "ZAI_API_KEY",        "ZAI_BASE_URL",        "ZAI_MODEL",
     "https://api.z.ai/v1",                             "claude-sonnet-4-20250514", "zai"),
    ("Anthropic",     "ANTHROPIC_API_KEY",  "ANTHROPIC_BASE_URL",  "ANTHROPIC_MODEL",
     "https://api.anthropic.com/v1",                    "claude-sonnet-4-20250514", "anthropic"),
    ("Volcengine Ark","ARK_API_KEY",        "ARK_BASE_URL",        "ARK_MODEL",
     "https://ark.cn-beijing.volces.com/api/coding/v3", "doubao-seed-2.0-code",     "volcengine"),
    ("OpenAI",        "OPENAI_API_KEY",     "OPENAI_BASE_URL",     "OPENAI_MODEL",
     "https://api.openai.com/v1",                       "gpt-4o-mini",              "openai"),
    ("DeepSeek",      "DEEPSEEK_API_KEY",   "DEEPSEEK_BASE_URL",   "DEEPSEEK_MODEL",
     "https://api.deepseek.com/v1",                     "deepseek-chat",            "deepseek"),
    ("OpenRouter",    "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_MODEL",
     "https://openrouter.ai/api/v1",                    "anthropic/claude-3-5-haiku","openrouter"),
]

_PLACEHOLDER_VALUES = {"", "your_key_here", "REPLACE_ME", "your_volcengine_ark_key_here", "sk-xxx"}


@dataclass
class DetectedEndpoint:
    provider: str
    api_key: str
    base_url: str
    model: str
    source: str        # e.g. "OPENCLAW_API_KEY", "claude_oauth", "ollama_local"
    api_key_env: str   # env var name, empty for local/oauth


# ── Claude OAuth ──────────────────────────────────────────────────

def _load_claude_oauth() -> str | None:
    """Return a valid Claude OAuth access token, or None."""
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if not creds_path.exists():
        return None
    try:
        data = json.loads(creds_path.read_text())
        token = (
            data.get("claudeAiOauth", {}).get("accessToken")
            or data.get("access_token")
            or data.get("token")
        )
        return token if token else None
    except Exception:
        return None


# ── Main probe ────────────────────────────────────────────────────

def detect_endpoint() -> DetectedEndpoint | None:
    """Return the best available LLM endpoint, or None if nothing detected."""

    # Priority 0: Claude OAuth (~/.claude/.credentials.json)
    oauth_token = _load_claude_oauth()
    if oauth_token:
        return DetectedEndpoint(
            provider="anthropic",
            api_key=oauth_token,
            base_url="https://api.anthropic.com/v1",
            model="claude-sonnet-4-20250514",
            source="claude_oauth",
            api_key_env="",
        )

    # Priority 1–7: API key env vars (checked in _PROBE_TABLE order)
    for display, env_var, base_url_env, model_env, default_base, default_model, provider in _PROBE_TABLE:
        val = os.getenv(env_var, "").strip()
        if not val or val in _PLACEHOLDER_VALUES:
            continue
        base_url = os.getenv(base_url_env, default_base).strip() or default_base
        model    = os.getenv(model_env, default_model).strip()   or default_model
        return DetectedEndpoint(
            provider=provider, api_key=val,
            base_url=base_url, model=model,
            source=env_var, api_key_env=env_var,
        )

    # Priority 8: LM Studio (localhost:1234)
    if _port_open("localhost", 1234):
        return DetectedEndpoint(
            provider="lm_studio", api_key="no-key",
            base_url="http://localhost:1234/v1", model="loaded-model",
            source="lm_studio_local", api_key_env="",
        )

    # Priority 9: Ollama (localhost:11434)
    if _port_open("localhost", 11434):
        return DetectedEndpoint(
            provider="ollama", api_key="no-key",
            base_url="http://localhost:11434/v1", model="llama3.1",
            source="ollama_local", api_key_env="",
        )

    return None


def probe_llm_env(endpoint) -> tuple[bool, str]:
    """Check if an LLMEndpoint is usably configured.

    Returns:
        (True, source_description)  — configured and ready
        (False, guidance_message)   — nothing usable found
    """
    from ..config import LLMEndpoint as _LLMEndpoint

    # Already has a real key / non-default base_url
    if isinstance(endpoint, _LLMEndpoint):
        if endpoint.api_key and endpoint.api_key not in _PLACEHOLDER_VALUES:
            return True, endpoint.api_key_env or "config.yaml"
        if endpoint.base_url and "localhost" in endpoint.base_url:
            return True, "local"

    # Fall back to auto-detect
    ep = detect_endpoint()
    if ep:
        return True, ep.source
    return False, (
        "No LLM API key found.\n"
        "Set one of: OPENCLAW_API_KEY, ARK_API_KEY, ZAI_API_KEY, OPENAI_API_KEY, "
        "ANTHROPIC_API_KEY, DEEPSEEK_API_KEY\n"
        "Or install Claude Code (npm i -g @anthropic-ai/claude-code) to use OAuth for free."
    )


def apply_env_override(config, *, silent: bool = False) -> bool:
    """Detect the best available LLM and patch config.llm.text in-place.

    Only patches if the current endpoint is unconfigured (no key, no local URL).
    Returns True if an endpoint was found and applied.
    """
    ep = config.llm.text

    # Already has a usable key — don't override
    if ep.api_key and ep.api_key not in _PLACEHOLDER_VALUES:
        return True
    if ep.base_url and "localhost" in ep.base_url:
        return True

    detected = detect_endpoint()
    if not detected:
        return False

    ep.provider    = detected.provider
    ep.api_key_env = detected.api_key_env
    ep.base_url    = detected.base_url
    ep.model       = detected.model or ep.model

    # Patch the actual env var so OpenAI client can read it
    if detected.api_key and detected.api_key_env:
        os.environ[detected.api_key_env] = detected.api_key
    elif detected.source == "claude_oauth":
        # Inject OAuth token as ANTHROPIC_API_KEY for SDK compatibility
        os.environ.setdefault("ANTHROPIC_API_KEY", detected.api_key)
        ep.api_key_env = "ANTHROPIC_API_KEY"

    if not silent:
        logger.info("LLM auto-detected: %s via %s", detected.model, detected.source)

    return True


# ── Utilities ─────────────────────────────────────────────────────

def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Return True if a TCP port is open (local LLM server running)."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
