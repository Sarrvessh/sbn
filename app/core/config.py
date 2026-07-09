"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for backend services."""

    app_name: str = "SBN — ARMS"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+psycopg2://sbn:sbn_password@localhost:5432/ai_observability",
        validation_alias="DATABASE_URL",
    )

    metrics_window_size: int = Field(default=50, ge=1, le=500)

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    openai_referer: str | None = Field(default=None, validation_alias="OPENAI_REFERER")
    openai_app_title: str | None = Field(default=None, validation_alias="OPENAI_APP_TITLE")
    default_agent_model: str = Field(
        default="gpt-4o-mini", validation_alias="DEFAULT_AGENT_MODEL"
    )
    latency_alert_threshold_ms: float = Field(
        default=1500.0,
        ge=10.0,
        validation_alias="LATENCY_ALERT_THRESHOLD_MS",
    )
    cost_alert_threshold: float = Field(
        default=0.05, ge=0.0, validation_alias="COST_ALERT_THRESHOLD",
    )
    budget_alert_threshold_pct: float = Field(
        default=80.0, ge=0.0, le=100.0, validation_alias="BUDGET_ALERT_THRESHOLD_PCT",
    )
    api_key_header_name: str = Field(default="X-API-Key", validation_alias="API_KEY_HEADER_NAME")

    bootstrap_admin_api_key: str = Field(
        default="",
        validation_alias="BOOTSTRAP_ADMIN_API_KEY",
    )
    bootstrap_analyst_api_key: str = Field(
        default="",
        validation_alias="BOOTSTRAP_ANALYST_API_KEY",
    )
    bootstrap_viewer_api_key: str = Field(
        default="",
        validation_alias="BOOTSTRAP_VIEWER_API_KEY",
    )
    bootstrap_ingest_api_key: str = Field(
        default="",
        validation_alias="BOOTSTRAP_INGEST_API_KEY",
    )
    bootstrap_analyst_project_scope: str | None = Field(
        default=None,
        validation_alias="BOOTSTRAP_ANALYST_PROJECT_SCOPE",
    )
    bootstrap_viewer_project_scope: str | None = Field(
        default=None,
        validation_alias="BOOTSTRAP_VIEWER_PROJECT_SCOPE",
    )
    encryption_key: str = Field(
        default="change-me-to-a-secret-key-32bytes",
        validation_alias="SBN_ENCRYPTION_KEY",
    )

    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ALLOW_ORIGINS",
    )

    db_pool_size: int = Field(default=10, ge=1, le=100, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, ge=0, le=100, validation_alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, ge=1, validation_alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, ge=60, validation_alias="DB_POOL_RECYCLE")

    rate_limit_per_minute: int = Field(default=60, ge=1, validation_alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_enabled: bool = Field(default=True, validation_alias="RATE_LIMIT_ENABLED")

    trusted_hosts: str = Field(
        default="localhost,127.0.0.1,0.0.0.0",
        validation_alias="TRUSTED_HOSTS",
    )
    enforce_trusted_hosts: bool = Field(
        default=False, validation_alias="ENFORCE_TRUSTED_HOSTS",
    )

    app_start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_required_for_prod(self) -> list[str]:
        errors: list[str] = []
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        if not self.encryption_key or self.encryption_key == "change-me-to-a-secret-key-32bytes":
            errors.append("SBN_ENCRYPTION_KEY must be set to a secure random value")
        if self.bootstrap_admin_api_key == "admin-local-dev-key":
            errors.append("BOOTSTRAP_ADMIN_API_KEY must be changed from the default dev value")
        return errors


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()


def get_cors_origins() -> list[str]:
    """Parse comma-separated CORS origins from settings."""
    origins = [item.strip() for item in settings.cors_allow_origins.split(",") if item.strip()]
    return origins or ["*"]