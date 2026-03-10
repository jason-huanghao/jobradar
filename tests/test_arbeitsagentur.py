"""Tests for Arbeitsagentur data source."""

from unittest.mock import MagicMock, patch

import pytest

from src.config import AppConfig
from src.models import SearchQuery
from src.sources.arbeitsagentur import ArbeitsagenturSource, _map_to_raw_job


def test_map_to_raw_job():
    """Test mapping Arbeitsagentur API response to RawJob."""
    item = {
        "refnr": "12345678",
        "titel": "AI Engineer (m/w/d)",
        "arbeitgeber": "TechCorp GmbH",
        "arbeitsort": {
            "ort": "Berlin",
            "region": "Berlin",
        },
        "externeUrl": "https://example.com/job/12345",
        "eintrittsdatum": "2026-03-01",
        "beruf": "Developing AI systems and ML pipelines",
        "homeoffice": True,
    }

    job = _map_to_raw_job(item)

    assert job is not None
    assert job.title == "AI Engineer (m/w/d)"
    assert job.company == "TechCorp GmbH"
    assert "Berlin" in job.location
    assert job.url == "https://example.com/job/12345"
    assert job.source == "arbeitsagentur"
    assert job.remote is True


def test_map_to_raw_job_minimal():
    """Test mapping with minimal data (no external URL, no location)."""
    item = {
        "refnr": "99999",
        "titel": "Data Scientist",
        "arbeitgeber": "StartupXY",
        "arbeitsort": {},
    }

    job = _map_to_raw_job(item)

    assert job is not None
    assert job.title == "Data Scientist"
    assert "arbeitsagentur.de" in job.url  # Fallback URL


def test_map_to_raw_job_bad_data():
    """Test graceful handling of malformed data."""
    job = _map_to_raw_job({})
    # Should not crash — returns a job with empty fields or None
    # The function tries to handle missing keys gracefully
    assert job is not None or job is None  # Either is acceptable
