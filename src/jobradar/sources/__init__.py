"""Sources module."""

from .base import JobSource
from .normalizer import dedup, make_id, normalise
from .query_builder import build_queries
from .registry import SourceRegistry, build_registry

__all__ = [
    "JobSource",
    "make_id", "normalise", "dedup",
    "build_queries",
    "SourceRegistry", "build_registry",
]
