"""Tests for JobSpy adapter."""

from src.sources.jobspy_adapter import _map_row_to_raw_job


class MockRow(dict):
    """Dict that also supports .get() like a pandas row."""
    pass


def test_map_row_to_raw_job():
    """Test mapping a JobSpy DataFrame row to RawJob."""
    row = MockRow({
        "title": "ML Engineer",
        "company_name": "DataCo",
        "location": "Hamburg, Germany",
        "job_url": "https://indeed.com/job/12345",
        "description": "Looking for ML engineer with Python and PyTorch.",
        "date_posted": "2026-03-01",
        "is_remote": False,
        "job_type": "fulltime",
        "min_amount": 60000,
        "max_amount": 80000,
        "currency": "EUR",
    })

    job = _map_row_to_raw_job(row, "indeed")

    assert job is not None
    assert job.title == "ML Engineer"
    assert job.company == "DataCo"
    assert job.source == "jobspy:indeed"
    assert "60000" in job.salary


def test_map_row_missing_title():
    """Test that rows without title are skipped."""
    row = MockRow({
        "title": "",
        "company_name": "Unknown",
    })

    job = _map_row_to_raw_job(row, "google")
    assert job is None
