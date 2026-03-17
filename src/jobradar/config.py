"""Application configuration — loaded from config.yaml + .env.

Design principle: every field has a working default.
The only required user input is a CV path/URL.
Profile YAML is stored at ~/.jobradar/profile.yaml (user-global, survives reinstalls).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, PrivateAttr

_JOBRADAR_DIR = Path.home() / ".jobradar"


# ── Sub-models ────────────────────────────────────────────────────


class LLMEndpoint(BaseModel):
    provider: str = "auto"
    model: str = ""
    base_url: str = ""
    api_key_env: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    rate_limit_delay: float = 1.0

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "") if self.api_key_env else ""

class LLMConfig(BaseModel):
    text: LLMEndpoint = Field(default_factory=LLMEndpoint)


class CandidateConfig(BaseModel):
    # Primary field — path, URL, or blank (will prompt)
    cv: str = ""
    # Legacy alias (backward compat with existing config.yaml files)
    cv_path: str = ""
    # User-global profile cache — survives project reinstalls
    profile_yaml: str = str(_JOBRADAR_DIR / "profile.yaml")

    def effective_cv(self) -> str:
        """Return the active CV source, preferring 'cv' over legacy 'cv_path'."""
        return (self.cv or self.cv_path).strip()


class SearchConfig(BaseModel):
    # Empty = worldwide (no location filter applied to queries)
    locations: list[str] = Field(default_factory=list)
    radius_km: int = 50
    postal_code: str = ""
    max_results_per_source: int = 20
    max_days_old: int = 14
    quick_max_results: int = 5
    job_types: list[str] = Field(default_factory=lambda: ["fulltime"])
    custom_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(
        default_factory=lambda: ["Praktikum", "Werkstudent", "internship", "Ausbildung"]
    )
    exclude_companies: list[str] = Field(default_factory=list)


class SourceConfig(BaseModel):
    enabled: bool = False
    boards: list[str] = Field(default_factory=list)
    country: str = "germany"


class BossZhipinConfig(BaseModel):
    enabled: bool = False
    city_code: str = "101010100"
    max_results_per_source: int = 50
    max_pages: int = 3
    delay_between_requests: float = 3.0


class LagouConfig(BaseModel):
    enabled: bool = False
    city_code: str = "101020100"
    max_results_per_source: int = 50
    max_pages: int = 3
    delay_between_requests: float = 3.0


class ZhilianConfig(BaseModel):
    enabled: bool = False
    city_code: str = "538"
    max_results_per_source: int = 50


class SourcesConfig(BaseModel):
    arbeitsagentur: SourceConfig = Field(default_factory=lambda: SourceConfig(enabled=True))
    jobspy: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=True, boards=["indeed", "google"], country="germany"
        )
    )
    stepstone: SourceConfig = Field(default_factory=lambda: SourceConfig(enabled=True))
    xing: SourceConfig = Field(default_factory=lambda: SourceConfig(enabled=True))
    bosszhipin: BossZhipinConfig = Field(default_factory=BossZhipinConfig)
    lagou: LagouConfig = Field(default_factory=LagouConfig)
    zhilian: ZhilianConfig = Field(default_factory=ZhilianConfig)


class ScoringConfig(BaseModel):
    min_score_digest: float = 6.0
    min_score_application: float = 7.0
    auto_apply_min_score: float = 7.5
    batch_size: int = 5
    dimensions: list[str] = Field(
        default_factory=lambda: [
            "skills_match", "seniority_fit", "location_fit",
            "language_fit", "visa_friendly", "growth_potential",
        ]
    )


class ReportConfig(BaseModel):
    """Static HTML report — deployed to GitHub Pages (opt-in)."""
    github_pages_enabled: bool = False
    github_repo: str = ""
    report_branch: str = "gh-pages"
    report_dir: str = str(_JOBRADAR_DIR / "reports")


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 7842
    open_browser: bool = True
    db_path: str = str(_JOBRADAR_DIR / "jobradar.db")
    cache_dir: str = str(_JOBRADAR_DIR / "cache")


class AppConfig(BaseModel):
    candidate: CandidateConfig = Field(default_factory=CandidateConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    _config_dir: Path = PrivateAttr(default_factory=lambda: Path("."))

    def resolve_path(self, p: str) -> Path:
        path = Path(p).expanduser()
        if path.is_absolute():
            return path
        return (self._config_dir / path).resolve()


# ── Loader ────────────────────────────────────────────────────────


def load_config(config_path: Path | None = None, cv_override: str | None = None) -> AppConfig:
    """Load config.yaml + .env. Auto-detect LLM from environment."""
    if config_path is None:
        config_path = _find_config()

    env_path = config_path.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Also load ~/.jobradar/.env if it exists (user-global keys)
    global_env = _JOBRADAR_DIR / ".env"
    if global_env.exists():
        load_dotenv(global_env, override=False)

    raw: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    _normalize_raw(raw)

    config = AppConfig(**raw)
    config._config_dir = config_path.parent

    if cv_override:
        config.candidate.cv = cv_override

    from .llm.env_probe import apply_env_override
    apply_env_override(config, silent=True)

    return config


def _normalize_raw(raw: dict) -> None:
    """Map minimal config keys to nested structure (backward compat)."""
    search = raw.get("search", {})
    if "max_results" in search and "max_results_per_source" not in search:
        search["max_results_per_source"] = search.pop("max_results")

    scoring = raw.get("scoring", {})
    if "min_score" in scoring and "min_score_digest" not in scoring:
        scoring["min_score_digest"] = scoring.pop("min_score")

    # Support top-level  candidate.cv_path  in YAML as  candidate.cv
    candidate = raw.get("candidate", {})
    if "cv_path" in candidate and "cv" not in candidate:
        candidate["cv"] = candidate.pop("cv_path")


def _find_config() -> Path:
    """Walk upward from cwd then check ~/.jobradar/config.yaml."""
    here = Path.cwd()
    for parent in [here, *here.parents]:
        candidate = parent / "config.yaml"
        if candidate.exists():
            return candidate
    global_cfg = _JOBRADAR_DIR / "config.yaml"
    if global_cfg.exists():
        return global_cfg
    return here / "config.yaml"
