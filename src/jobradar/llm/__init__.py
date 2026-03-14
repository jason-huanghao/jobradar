"""LLM module — client + environment probe."""

from .client import LLMClient
from .env_probe import apply_env_override, probe_llm_env

__all__ = ["LLMClient", "probe_llm_env", "apply_env_override"]
