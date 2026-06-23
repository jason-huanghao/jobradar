"""Curated LLM provider catalog — single source of truth for the setup wizard,
the settings UI/API, and the test-connection surface.

Each entry describes an OpenAI-compatible endpoint. Secret keys are never stored
here (or in the DB) — only the *name* of the env var that holds the key.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    base_url: str
    default_model: str
    api_key_env: str          # "" for local servers and custom
    local: bool = False       # True = no API key required (local server)
    supports_json_mode: bool = True
    # Extra HTTP headers sent on every request (e.g. a client User-Agent some
    # coding endpoints expect). Merged into the OpenAI client at construction.
    default_headers: dict[str, str] = field(default_factory=dict)
    # Some models reject any temperature but a fixed value. When set, the client
    # ignores caller/config temperature and always sends this one.
    forced_temperature: float | None = None


# Curated, ordered for the wizard. ``custom`` is the OpenAI-compatible escape hatch.
CATALOG: list[Provider] = [
    Provider("volcengine", "Volcengine Ark (doubao)",
             "https://ark.cn-beijing.volces.com/api/coding/v3",
             "doubao-seed-2.0-code", "ARK_API_KEY", supports_json_mode=False),
    Provider("zai", "Z.AI (Claude proxy)",
             "https://api.z.ai/v1", "claude-sonnet-4-20250514", "ZAI_API_KEY"),
    Provider("openai", "OpenAI",
             "https://api.openai.com/v1", "gpt-4o-mini", "OPENAI_API_KEY"),
    Provider("deepseek", "DeepSeek",
             "https://api.deepseek.com/v1", "deepseek-chat", "DEEPSEEK_API_KEY"),
    Provider("kimi", "Kimi (coding)",
             "https://api.kimi.com/coding/v1", "kimi-for-coding", "KIMI_API_KEY",
             default_headers={"User-Agent": "KimiCLI/1.5"}, forced_temperature=1.0),
    Provider("openrouter", "OpenRouter",
             "https://openrouter.ai/api/v1", "anthropic/claude-3-5-haiku",
             "OPENROUTER_API_KEY"),
    Provider("anthropic", "Anthropic",
             "https://api.anthropic.com/v1", "claude-sonnet-4-20250514",
             "ANTHROPIC_API_KEY"),
    Provider("ollama", "Ollama (local)",
             "http://localhost:11434/v1", "llama3.1", "",
             local=True, supports_json_mode=False),
    Provider("lm_studio", "LM Studio (local)",
             "http://localhost:1234/v1", "loaded-model", "",
             local=True, supports_json_mode=False),
]

CUSTOM = Provider(
    "custom", "Custom (OpenAI-compatible)", "", "", "",
    supports_json_mode=True,
)

# All selectable options, custom last.
ALL: list[Provider] = [*CATALOG, CUSTOM]


def get_provider(provider_id: str) -> Provider | None:
    for p in ALL:
        if p.id == provider_id:
            return p
    return None
