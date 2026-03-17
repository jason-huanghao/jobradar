"""Unified LLM client — wraps any OpenAI-compatible API with retry + JSON parsing."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import OpenAI

from ..config import LLMEndpoint

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0


class LLMClient:
    """Single entry point for all LLM calls in JobRadar.

    Supports:
    - Single-turn completion          → complete()
    - JSON-mode completion            → complete_json()
    - Structured (no json_mode flag)  → complete_structured()
    - Batched prompts                 → batch()
    """

    def __init__(self, endpoint: LLMEndpoint) -> None:
        self.endpoint = endpoint
        self._client = OpenAI(
            api_key=endpoint.api_key or "no-key",
            base_url=endpoint.base_url,
        )

    def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Single-turn completion → raw text."""
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
                resp = self._client.chat.completions.create(**kwargs)
                return (resp.choices[0].message.content or "").strip()
            except Exception as exc:
                logger.warning("LLM attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc)
                if attempt == _MAX_RETRIES:
                    raise
                time.sleep(_RETRY_BASE_DELAY * attempt)

        return ""  # unreachable

    def complete_json(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
    ) -> dict | list:
        """Complete with json_mode=True → parsed Python object."""
        raw = self.complete(prompt, system=system, temperature=temperature, json_mode=True)
        return _parse_json(raw)

    def complete_structured(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
    ) -> dict | list:
        """Complete without json_mode (for providers that don't support it) → parsed object."""
        raw = self.complete(prompt, system=system, temperature=temperature)
        return _parse_json(raw)

    def complete_auto(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float | None = None,
    ) -> dict | list:
        """Try json_mode first; fall back to structured parsing.

        Handles providers like Volcengine Ark that don't support response_format.
        """
        if self.endpoint.provider in ("volcengine", "ollama", "lm_studio"):
            return self.complete_structured(prompt, system=system, temperature=temperature)
        try:
            return self.complete_json(prompt, system=system, temperature=temperature)
        except Exception:
            logger.warning("json_mode failed, retrying with structured parsing")
            return self.complete_structured(prompt, system=system, temperature=temperature)

    def batch(
        self,
        prompts: list[str],
        *,
        system: str = "",
        temperature: float | None = None,
    ) -> list[str]:
        """Run multiple prompts sequentially, respecting rate_limit_delay."""
        results = []
        for i, prompt in enumerate(prompts):
            if i > 0:
                time.sleep(self.endpoint.rate_limit_delay)
            results.append(self.complete(prompt, system=system, temperature=temperature))
        return results


def _parse_json(text: str) -> dict | list:
    """Parse JSON from LLM output, stripping markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed: %s\nRaw (first 500): %s", exc, text[:500])
        raise
