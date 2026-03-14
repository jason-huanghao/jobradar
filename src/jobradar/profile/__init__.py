"""Profile module — CV ingestion and extraction."""

from .extractor import extract_profile
from .ingestor import ingest

__all__ = ["ingest", "extract_profile"]
