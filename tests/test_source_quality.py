"""Source data-quality tests (improve/source-data-quality).

Root cause of poor CV matches: 3 of 4 working sources returned jobs with empty
descriptions, so the LLM scored on title only. These tests pin the fixes:
richer scorer budget, linkedin description fetch, correct stepstone job URLs,
deterministic xing IDs, and detail-page description enrichment.

No live network: httpx is monkeypatched; the LLM is faked.
"""
from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup

from jobradar.models.job import RawJob, SearchQuery

NOW = datetime(2026, 6, 23, 12, 0, 0)


# ── 1. Scorer description budget ───────────────────────────────────
def test_scorer_default_budget_is_generous():
    from jobradar.scoring import scorer
    assert scorer._MAX_DESC_CHARS >= 2000


def test_truncate_respects_explicit_budget():
    from jobradar.scoring.scorer import _truncate_jobs
    job = RawJob(id="j", title="t", url="u", source="s", description="A" * 5000)
    out = _truncate_jobs([job], 2000)
    # 2000 chars + the ellipsis marker
    assert out[0].description.startswith("A" * 2000)
    assert len(out[0].description) == 2001
    # original untouched
    assert len(job.description) == 5000


def test_score_jobs_threads_budget_into_prompt():
    from jobradar.models.candidate import CandidateProfile
    from jobradar.scoring import scorer

    captured = {}

    class FakeLLM:
        def complete_auto(self, prompt, **k):
            captured["prompt"] = prompt
            return [{"score": 7.0, "breakdown": {}, "reasoning": "ok"}]

    prof = CandidateProfile()
    prof.personal.name = "X"
    job = RawJob(id="j", title="ML", url="http://x/1", source="s", description="B" * 5000)
    scorer.score_jobs([job], prof, FakeLLM(), batch_size=5, max_desc_chars=1500)
    assert "B" * 1500 in captured["prompt"]
    assert "B" * 1600 not in captured["prompt"]


# ── 2. jobspy linkedin description fetch ───────────────────────────
def _fake_scrape_capture(calls):
    import pandas as pd

    def _scrape(**kwargs):
        calls.append(kwargs)
        return pd.DataFrame()
    return _scrape


def test_jobspy_linkedin_requests_descriptions(monkeypatch):
    import jobspy

    from jobradar.sources.adapters.jobspy_adapter import JobSpySource

    calls: list = []
    monkeypatch.setattr(jobspy, "scrape_jobs", _fake_scrape_capture(calls))
    q = SearchQuery(keyword="ml", location="Berlin", source="jobspy:linkedin",
                    extra={"board": "linkedin", "max_results": 5, "country": "germany"})
    JobSpySource().fetch([q], NOW)
    assert calls and calls[0].get("linkedin_fetch_description") is True


def test_jobspy_indeed_no_linkedin_flag(monkeypatch):
    import jobspy

    from jobradar.sources.adapters.jobspy_adapter import JobSpySource

    calls: list = []
    monkeypatch.setattr(jobspy, "scrape_jobs", _fake_scrape_capture(calls))
    q = SearchQuery(keyword="ml", location="Berlin", source="jobspy:indeed",
                    extra={"board": "indeed", "max_results": 5, "country": "germany"})
    JobSpySource().fetch([q], NOW)
    assert calls and not calls[0].get("linkedin_fetch_description")


# ── 3. StepStone extracts the job URL, not the company page ─────────
def test_stepstone_article_extracts_job_url():
    from jobradar.sources.adapters.stepstone import _parse_article
    html = (
        '<article data-testid="job-item">'
        '  <a href="/cmp/de/inovex-gmbh-24494/jobs">inovex GmbH</a>'
        '  <h2><a href="/stellenangebote--ML-Engineer--12345-inline.html">ML Engineer</a></h2>'
        "</article>"
    )
    art = BeautifulSoup(html, "html.parser").select_one("article")
    job = _parse_article(art)
    assert job is not None
    assert "stellenangebote" in job.url
    assert "/cmp/" not in job.url


# ── 4. XING IDs are deterministic (no process-salted hash()) ───────
def test_xing_ids_deterministic_and_sha():
    from jobradar.sources.adapters.xing import _parse_jsonld
    item = {"@type": "JobPosting", "title": "ML Eng",
            "url": "https://www.xing.com/jobs/berlin-ml-1"}
    a = _parse_jsonld(item)
    b = _parse_jsonld(item)
    assert a.id == b.id
    assert len(a.id) == 16  # make_id sha256[:16], not "xing-<hash>"


# ── 5. Detail-page description enrichment ──────────────────────────
class _Resp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


_XING_DETAIL = """
<html><head>
<script type="application/ld+json">
{"@type":"JobPosting","title":"ML Eng",
 "description":"<div><p>We need <b>SPARQL</b> and causal inference.</p></div>"}
</script></head><body></body></html>
"""


def test_xing_fetch_detail_strips_html(monkeypatch):
    import httpx

    from jobradar.sources.adapters.xing import XingSource

    monkeypatch.setattr(httpx.Client, "get",
                        lambda self, *a, **k: _Resp(200, _XING_DETAIL))
    job = RawJob(id="x1", title="ML Eng", url="https://www.xing.com/jobs/berlin-ml-1",
                 source="xing")
    desc = XingSource().fetch_detail(job)
    assert "SPARQL" in desc and "causal inference" in desc
    assert "<div>" not in desc and "<b>" not in desc


def test_base_fetch_detail_default_empty():
    from jobradar.sources.base import JobSource

    class Dummy(JobSource):
        source_id = "dummy"

        def fetch(self, queries, since):
            return []

    assert Dummy().fetch_detail(RawJob(id="d", title="t", url="u", source="dummy")) == ""


def test_registry_enrich_fills_only_thin_descriptions():
    from jobradar.sources.base import JobSource
    from jobradar.sources.registry import SourceRegistry

    class FakeSrc(JobSource):
        source_id = "fake"

        def fetch(self, queries, since):
            return []

        def fetch_detail(self, job):
            return "ENRICHED DESCRIPTION " * 20  # long, real content

    reg = SourceRegistry()
    reg.register(FakeSrc())
    thin = RawJob(id="a", title="t", url="https://x/a", source="fake", description="")
    full = RawJob(id="b", title="t", url="https://x/b", source="fake",
                  description="X" * 500)
    no_url = RawJob(id="c", title="t", url="", source="fake", description="")
    n = reg.enrich_descriptions([thin, full, no_url], cap=10)
    assert n == 1
    assert "ENRICHED" in thin.description
    assert full.description == "X" * 500          # untouched
    assert no_url.description == ""               # no URL → skipped


def test_registry_enrich_respects_cap():
    from jobradar.sources.base import JobSource
    from jobradar.sources.registry import SourceRegistry

    class FakeSrc(JobSource):
        source_id = "fake"

        def __init__(self):
            self.detail_calls = 0

        def fetch(self, queries, since):
            return []

        def fetch_detail(self, job):
            self.detail_calls += 1
            return "DESC " * 50

    src = FakeSrc()
    reg = SourceRegistry()
    reg.register(src)
    jobs = [RawJob(id=str(i), title="t", url=f"https://x/{i}", source="fake",
                   description="") for i in range(10)]
    n = reg.enrich_descriptions(jobs, cap=3)
    assert n == 3
    assert src.detail_calls == 3


def test_registry_enrich_survives_source_errors():
    from jobradar.sources.base import JobSource
    from jobradar.sources.registry import SourceRegistry

    class BoomSrc(JobSource):
        source_id = "boom"

        def fetch(self, queries, since):
            return []

        def fetch_detail(self, job):
            raise RuntimeError("detail blew up")

    reg = SourceRegistry()
    reg.register(BoomSrc())
    job = RawJob(id="a", title="t", url="https://x/a", source="boom", description="")
    n = reg.enrich_descriptions([job], cap=5)  # must not raise
    assert n == 0
    assert job.description == ""
