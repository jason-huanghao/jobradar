"""Shared utilities used across pipeline, API, and interfaces."""

from __future__ import annotations

import hashlib

from .models.candidate import CandidateProfile


def profile_id(profile: CandidateProfile) -> str:
    """Stable 16-char ID for a candidate profile snapshot."""
    return hashlib.sha256(profile.model_dump_json().encode()).hexdigest()[:16]
