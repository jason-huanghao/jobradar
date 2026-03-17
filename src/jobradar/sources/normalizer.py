"""Normalise raw adapter output to RawJob with a deterministic dedup ID."""

from __future__ import annotations

import hashlib

from ..models.job import RawJob


def make_id(source: str, url: str, title: str = "", company: str = "") -> str:
    """Deterministic ID: sha256(source + canonical_url)."""
    key = source + (url.strip().lower() or f"{title}|{company}".lower())
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def normalise(job: RawJob) -> RawJob:
    """Ensure job.id is set and consistent. Mutates in-place, returns job."""
    if not job.id:
        job.id = make_id(job.source, job.url, job.title, job.company)
    return job


def dedup(jobs: list[RawJob]) -> list[RawJob]:
    """Remove duplicates within a batch, keeping first occurrence."""
    seen: set[str] = set()
    out: list[RawJob] = []
    for job in jobs:
        if job.id not in seen:
            seen.add(job.id)
            out.append(job)
    return out
