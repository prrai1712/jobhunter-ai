"""Application settings — Pydantic Settings v2 with .env support.

All configuration is loaded from environment variables with sensible defaults.
Group settings by concern for clarity and maintainability.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection and pool settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://jobhunter:changeme@localhost:5432/jobhunter",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://jobhunter:changeme@localhost:5432/jobhunter",
        alias="DATABASE_URL_SYNC",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")


class TelegramSettings(BaseSettings):
    """Telegram bot credentials and authorization."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    allowed_user_id: int = Field(default=0, alias="TELEGRAM_ALLOWED_USER_ID")
    log_chat_id: int = Field(default=0, alias="TELEGRAM_LOG_CHAT_ID")


class CandidateSettings(BaseSettings):
    """Candidate profile loaded from environment."""

    model_config = SettingsConfigDict(env_prefix="CANDIDATE_", env_file=".env", extra="ignore")

    name: str = "Priyanshu Rai"
    email: str = "ppprai1712@gmail.com"
    phone: str = "8103723400"
    country: str = "India"
    current_position: str = "Software Engineer"
    current_company: str = "Park+"
    experience_years: int = 1


class JobFilterSettings(BaseSettings):
    """Filters for job eligibility."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    min_salary_lpa: float = Field(default=15.0, alias="MIN_SALARY_LPA")
    min_match_score: int = Field(default=85, alias="MIN_MATCH_SCORE")
    min_experience_years: int = Field(default=1, alias="MIN_EXPERIENCE_YEARS")
    max_experience_years: int = Field(default=4, alias="MAX_EXPERIENCE_YEARS")
    target_roles: list[str] = Field(
        default=[
            "Backend Engineer",
            "Software Engineer",
            "Python Developer",
            "Django Developer",
            "SDE-1",
            "SDE-2",
        ],
        alias="TARGET_ROLES",
    )
    candidate_skills: list[str] = Field(
        default=[
            "Python",
            "Django",
            "REST APIs",
            "MySQL",
            "PostgreSQL",
            "Redis",
            "Celery",
            "Docker",
            "Git",
            "Linux",
            "Web Scraping",
            "Distributed Systems",
            "Backend Engineering",
        ],
        alias="CANDIDATE_SKILLS",
    )

    @field_validator("target_roles", "candidate_skills", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: Any) -> list[str]:
        """Parse comma-separated string into a list."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v  # type: ignore[return-value]


class SchedulerSettings(BaseSettings):
    """Task scheduler intervals and timing."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    discover_interval_hours: float = Field(default=2.0, alias="DISCOVER_INTERVAL_HOURS")
    salary_estimate_interval_hours: float = Field(
        default=2.5, alias="SALARY_ESTIMATE_INTERVAL_HOURS"
    )
    match_interval_hours: float = Field(default=3.0, alias="MATCH_INTERVAL_HOURS")
    apply_interval_hours: float = Field(default=4.0, alias="APPLY_INTERVAL_HOURS")
    cleanup_hour: int = Field(default=3, alias="CLEANUP_HOUR")
    stats_hour: int = Field(default=23, alias="STATS_HOUR")
    stats_minute: int = Field(default=55, alias="STATS_MINUTE")
    health_check_interval_minutes: int = Field(default=30, alias="HEALTH_CHECK_INTERVAL_MINUTES")


class ApplicationSettings(BaseSettings):
    """Auto-apply behaviour controls."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    max_concurrent_applications: int = Field(default=3, alias="MAX_CONCURRENT_APPLICATIONS")
    max_application_retries: int = Field(default=3, alias="MAX_APPLICATION_RETRIES")
    application_retry_delay_seconds: int = Field(
        default=30, alias="APPLICATION_RETRY_DELAY_SECONDS"
    )
    max_daily_applications: int = Field(default=50, alias="MAX_DAILY_APPLICATIONS")


class StorageSettings(BaseSettings):
    """File storage paths."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    data_dir: Path = Field(default=Path("/app/data"), alias="DATA_DIR")
    resume_dir: Path = Field(default=Path("/app/data/resumes"), alias="RESUME_DIR")
    screenshot_dir: Path = Field(default=Path("/app/data/screenshots"), alias="SCREENSHOT_DIR")
    html_snapshot_dir: Path = Field(
        default=Path("/app/data/html_snapshots"), alias="HTML_SNAPSHOT_DIR"
    )
    report_dir: Path = Field(default=Path("/app/data/reports"), alias="REPORT_DIR")
    export_dir: Path = Field(default=Path("/app/data/exports"), alias="EXPORT_DIR")

    def ensure_dirs(self) -> None:
        """Create all storage directories if they don't exist."""
        for d in [
            self.data_dir,
            self.resume_dir,
            self.screenshot_dir,
            self.html_snapshot_dir,
            self.report_dir,
            self.export_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)


class JobSourceSettings(BaseSettings):
    """ATS board tokens for job discovery."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    greenhouse_boards: list[str] = Field(default=[], alias="GREENHOUSE_BOARDS")
    lever_companies: list[str] = Field(default=[], alias="LEVER_COMPANIES")
    ashby_boards: list[str] = Field(default=[], alias="ASHBY_BOARDS")

    @field_validator("greenhouse_boards", "lever_companies", "ashby_boards", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: Any) -> list[str]:
        """Parse comma-separated string into a list."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v  # type: ignore[return-value]


class LoggingSettings(BaseSettings):
    """Structured logging configuration."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_file: Path = Field(default=Path("/app/logs/jobhunter.log"), alias="LOG_FILE")


class AppSettings(BaseSettings):
    """Root settings — aggregates all sub-settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    environment: str = Field(default="production", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    # Sub-settings (loaded independently to support env prefix separation)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    candidate: CandidateSettings = Field(default_factory=CandidateSettings)
    job_filter: JobFilterSettings = Field(default_factory=JobFilterSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    application: ApplicationSettings = Field(default_factory=ApplicationSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    job_sources: JobSourceSettings = Field(default_factory=JobSourceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Singleton settings instance, cached after first load."""
    return AppSettings()
