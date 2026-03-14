"""Abstract base class for CV readers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ProfileReader(ABC):
    """Reads a CV from some source and returns raw plain text."""

    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """Return True if this reader can handle the given source string."""
        ...

    @abstractmethod
    def read(self, source: str) -> str:
        """Read the source and return plain text suitable for LLM processing."""
        ...
