"""Resolve the effective LLM endpoint for a user.

Per-user settings (stored on `UserSettings`) override the global `config.llm.text`.
Endpoint tuning (temperature/max_tokens/rate_limit) is always inherited from config.
"""

from __future__ import annotations

from ..config import AppConfig, LLMEndpoint
from ..storage.repo import get_user_settings


def resolve_endpoint(session, user_email: str, config: AppConfig) -> LLMEndpoint:
    base = config.llm.text
    s = get_user_settings(session, user_email)
    if s is None or not (s.provider or s.base_url):
        return base
    return LLMEndpoint(
        provider=s.provider or base.provider,
        model=s.model or base.model,
        base_url=s.base_url or base.base_url,
        api_key_env=s.api_key_env or base.api_key_env,
        temperature=base.temperature,
        max_tokens=base.max_tokens,
        rate_limit_delay=base.rate_limit_delay,
    )
