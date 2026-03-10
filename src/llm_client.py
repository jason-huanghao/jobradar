"""Unified OpenAI-compatible LLM client supporting Volcengine Ark and other providers."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import OpenAI

from .config import LLMEndpoint

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0


class LLMClient:
    """Thin wrapper around OpenAI-compatible APIs with retry logic."""

    def __init__(self, endpoint: LLMEndpoint) -> None:
        self.endpoint = endpoint
        self.client = OpenAI(
            api_key=endpoint.api_key or "no-key",
            base_url=endpoint.base_url,
        )
        # 读取延迟设置
        self.rate_limit_delay = getattr(endpoint, 'rate_limit_delay', 2.0)

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Send a single-turn completion and return the text response."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self.endpoint.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.endpoint.temperature,
            "max_tokens": max_tokens or self.endpoint.max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                return content.strip()
            except Exception as e:
                logger.warning("LLM call attempt %d/%d failed: %s", attempt, _MAX_RETRIES, e)
                if attempt == _MAX_RETRIES:
                    raise
                time.sleep(_RETRY_BASE_DELAY * attempt)

        return ""  # unreachable but keeps type checker happy

    def complete_json(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
    ) -> dict:
        """Complete and parse JSON response. Falls back to fence-stripping."""
        raw = self.complete(prompt, system=system, temperature=temperature, json_mode=True)
    def wait_for_rate_limit(self) -> None:
        """Wait for rate limiting."""
        time.sleep(self.rate_limit_delay)

    def complete_structured(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
    ) -> dict:
        """Complete expecting JSON but without json_mode (for providers that don't support it)."""
        raw = self.complete(prompt, system=system, temperature=temperature)
        return _parse_json(raw)


def _parse_json(text: str) -> dict:
    """Parse JSON from LLM output, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        # Remove ```json ... ``` wrapper
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON output: %s\nRaw: %s", e, text[:500])
        raise
