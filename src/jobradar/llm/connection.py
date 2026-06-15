"""Test-connection primitive — validate an LLM endpoint with one tiny call.

Shared by the CLI (`jobradar settings --test`, `jobradar health`) and the API
(`POST /api/settings/test`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ..config import LLMEndpoint
from .client import LLMClient


@dataclass
class ConnectionResult:
    ok: bool
    message: str
    latency_ms: int = 0


def test_connection(endpoint: LLMEndpoint, *, prompt: str = "Say OK.") -> ConnectionResult:
    """Issue one minimal completion against `endpoint`. Never raises."""
    started = time.monotonic()
    try:
        client = LLMClient(endpoint)
        reply = client.complete(prompt, temperature=0.0, max_tokens=8)
        latency = int((time.monotonic() - started) * 1000)
        return ConnectionResult(
            ok=True,
            message=f"OK ({endpoint.model}) → {reply!r}",
            latency_ms=latency,
        )
    except Exception as exc:
        latency = int((time.monotonic() - started) * 1000)
        return ConnectionResult(ok=False, message=str(exc), latency_ms=latency)
