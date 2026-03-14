"""Application configuration — loaded from config.yaml + .env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, PrivateAttr


# ── Sub-models ─────────────────────────────────────────────────────


class LLMEndpoint(BaseModel):
    provider: str = "volcengine"
    model: str = "doubao-seed-2.0-code"
    base_url: str = "https://ark.cn-beijing.volces.com/api/coding/v3"
    api_key_env: str = "ARK_API_KEY"
    temperature: float = 0.3
    max_tokens: int = 4096
    rate_limit_delay: float = 2.0

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "")


class LLMConfig(BaseModel):
    text: LLMEndpoint = Field(default_factory=LLMEndpoint)
    vision: LLMEndpoint | None = None
    embedding: LLMEndpoint | None = None


class CandidateConfig(BaseModel):
    cv_path: str = "./cv/cv_current.md"
    cv_url: str = ""
    profile_json_path: str = ""


class SearchConfig(BaseModel):
    locations: list[str] = Field(
        default_factory=lambda: ["Hannover", "Berlin", "Hamburg", "Remote"]
    )
    radius_km: int = 50
    postal_code: str = "30159"
    max_results_per_source: int = 50
    max_days_old: int = 14
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
    delay_between_requests: float = 2.0


class LagouConfig(BaseModel):
    enabled: bool = False
    city_code: str = "101020100"
    max_results_per_source: int = 50
    max_pages: int = 3
    delay_between_requests: float = 2.0


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
    batch_size: int = 5
    dimensions: list[str] = Field(
        default_factory=lambda: [
            "skills_match", "seniority_fit", "location_fit",
            "language_fit", "visa_friendly", "growth_potential",
        ]
    )


class OutputConfig(BaseModel):
    dir: str = "./outputs"
    excel_filename: str = "jobs_pipeline.xlsx"
    digest_dir: str = "digests"
    applications_dir: str = "applications"


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    from_addr: str = ""
    to_addr: str = ""
    app_password_env: str = "GMAIL_APP_PASSWORD"
    min_score_to_notify: float = 7.0


class ServerConfig(BaseModel):
    """FastAPI web server settings."""
    host: str = "127.0.0.1"
    port: int = 7842
    open_browser: bool = True
    db_path: str = "./jobradar.db"
    cache_dir: str = "./memory"


class AppConfig(BaseModel):
    candidate: CandidateConfig = Field(default_factory=CandidateConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    _config_dir: Path = PrivateAttr(default_factory=lambda: Path("."))

    def resolve_path(self, p: str) -> Path:
        path = Path(p)
        if path.is_absolute():
            return path
        return (self._config_dir / path).resolve()


# ── Loader ─────────────────────────────────────────────────────────


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load config.yaml + .env. Auto-detect LLM from environment.

    If config_path is None, searches for config.yaml starting from cwd
    and walking up to the filesystem root.
    """
    if config_path is None:
        config_path = _find_config()

    env_path = config_path.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    raw: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    config = AppConfig(**raw)
    config._config_dir = config_path.parent

    # Auto-detect LLM from environment
    from .llm.env_probe import apply_env_override
    apply_env_override(config, silent=True)

    return config


def _find_config() -> Path:
    """Walk upward from cwd looking for config.yaml."""
    here = Path.cwd()
    for parent in [here, *here.parents]:
        candidate = parent / "config.yaml"
        if candidate.exists():
            return candidate
    return here / "config.yaml"  # fallback (may not exist)
