"""Load and validate config.yaml into typed dataclass-like objects."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, PrivateAttr


# ── Config sub-models ──────────────────────────────────────────────


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
    cv_url: str = ""                      # Remote URL (overrides cv_path when set)
    profile_path: str = "./cv/profile.md"
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
    # Negative filters — applied before LLM scoring (free, saves tokens)
    exclude_keywords: list[str] = Field(
        default_factory=lambda: ["Praktikum", "Werkstudent", "internship", "Ausbildung"],
        description="Jobs whose title OR description contain any of these strings are dropped",
    )
    exclude_companies: list[str] = Field(
        default_factory=list,
        description="Companies to skip entirely (e.g. former employers)",
    )


class SourceConfig(BaseModel):
    enabled: bool = False
    boards: list[str] = Field(default_factory=list)
    country: str = "germany"
    adapter: str = ""
    mcp_command: str = ""
    mcp_args: list[str] = Field(default_factory=list)
    api_key_env: str = ""


class BossZhipinConfig(BaseModel):
    """BOSS直聘 scraper configuration."""
    enabled: bool = False
    city_code: str = "101010100"
    max_results_per_source: int = 50
    max_pages: int = 3
    delay_between_requests: float = 2.0


class LagouConfig(BaseModel):
    """拉勾网 scraper configuration."""
    enabled: bool = False
    city_code: str = "101020100"
    max_results_per_source: int = 50
    max_pages: int = 3
    delay_between_requests: float = 2.0


class ZhilianConfig(BaseModel):
    """智联招聘 scraper configuration."""
    enabled: bool = False
    city_code: str = "538"   # 538 = Shanghai; 530 = Beijing
    max_results_per_source: int = 50


class SourcesConfig(BaseModel):
    arbeitsagentur: SourceConfig = Field(
        default_factory=lambda: SourceConfig(enabled=True)
    )
    jobspy: SourceConfig = Field(
        default_factory=lambda: SourceConfig(
            enabled=True, boards=["indeed", "google"], country="germany"
        )
    )
    stepstone: SourceConfig = Field(default_factory=SourceConfig)
    linkedin: SourceConfig = Field(default_factory=SourceConfig)
    xing: SourceConfig = Field(default_factory=SourceConfig)
    scrapegraph: SourceConfig = Field(default_factory=SourceConfig)
    apify: SourceConfig = Field(default_factory=SourceConfig)
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


class ExcelOutputConfig(BaseModel):
    enabled: bool = True
    filename: str = "jobs_pipeline.xlsx"


class OutputConfig(BaseModel):
    dir: str = "./outputs"
    excel: ExcelOutputConfig = Field(default_factory=ExcelOutputConfig)
    digest: dict = Field(default_factory=lambda: {"enabled": True, "dir": "digests"})
    applications: dict = Field(default_factory=lambda: {"enabled": True, "dir": "applications"})


class RuntimeConfig(BaseModel):
    mode: str = "full"   # full | quick | dry-run
    log_level: str = "INFO"
    cache_dir: str = "./memory"
    skip_unchanged_cv: bool = True


class EmailNotificationConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    from_addr: str = ""
    to_addr: str = ""
    app_password_env: str = "GMAIL_APP_PASSWORD"
    min_score_to_notify: float = 7.0
    max_jobs_in_email: int = 10


class NotificationsConfig(BaseModel):
    email: EmailNotificationConfig = Field(default_factory=EmailNotificationConfig)


class WebConfig(BaseModel):
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    upload_dir: str = "./users"
    max_file_size_mb: int = 10
    max_concurrent_jobs: int = 5


# ── Root config ────────────────────────────────────────────────────


class AppConfig(BaseModel):
    """Root application configuration."""

    candidate: CandidateConfig = Field(default_factory=CandidateConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    web: WebConfig = Field(default_factory=WebConfig)

    # Private: set by load_config() after the YAML is parsed.
    # Using PrivateAttr ensures Pydantic v2 stores this per-instance,
    # not as a class-level variable (which would be shared across instances).
    _config_dir: Path = PrivateAttr(default_factory=lambda: Path("."))

    def resolve_path(self, p: str) -> Path:
        """Resolve a config-relative path."""
        path = Path(p)
        if path.is_absolute():
            return path
        return (self._config_dir / path).resolve()


# ── Loader ─────────────────────────────────────────────────────────


def load_config(config_path: Path) -> AppConfig:
    """Load config.yaml and .env, then auto-detect LLM from environment.

    Priority:
      1. config.yaml llm.text (if env var holds a valid key)
      2. Agent framework env vars (OpenClaw, Claude Code, Opencode, …)
      3. Generic provider env vars (OPENAI_API_KEY, DEEPSEEK_API_KEY, …)
      4. Local Ollama (if running)

    If no key is found anywhere the config is returned as-is and the
    caller (main.py) is responsible for showing setup guidance.
    """
    # Load .env from the config file's directory
    env_path = config_path.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    raw: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    config = AppConfig(**raw)
    config._config_dir = config_path.parent

    # Auto-detect LLM from environment (silent at load time; main.py logs result)
    from .llm_env_probe import apply_env_override, check_ollama_available
    found, _source = apply_env_override(config, silent=True)

    # Last resort: local Ollama
    if not found:
        ollama = check_ollama_available()
        if ollama:
            config.llm.text = LLMEndpoint(
                provider=ollama.provider,
                model=ollama.model,
                base_url=ollama.base_url,
                api_key_env="",
                temperature=config.llm.text.temperature,
                max_tokens=config.llm.text.max_tokens,
                rate_limit_delay=config.llm.text.rate_limit_delay,
            )

    return config
