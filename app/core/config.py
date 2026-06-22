"""Application configuration loaded from environment variables."""

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
        default="mysql+pymysql://sbn:sbn_password@mysql:3306/ai_observability",
        validation_alias="DATABASE_URL",
    )
    mongodb_url: str = Field(
        default="mongodb://mongo:27017/ai_observability",
        validation_alias="MONGODB_URL",
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
        default="admin-local-dev-key",
        validation_alias="BOOTSTRAP_ADMIN_API_KEY",
    )
    bootstrap_analyst_api_key: str = Field(
        default="analyst-local-dev-key",
        validation_alias="BOOTSTRAP_ANALYST_API_KEY",
    )
    bootstrap_viewer_api_key: str = Field(
        default="viewer-local-dev-key",
        validation_alias="BOOTSTRAP_VIEWER_API_KEY",
    )
    bootstrap_ingest_api_key: str = Field(
        default="ingest-local-dev-key",
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
    cors_allow_origins: str = Field(
        default="http://localhost:8501,http://127.0.0.1:8501",
        validation_alias="CORS_ALLOW_ORIGINS",
    )

    app_start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()


def get_cors_origins() -> list[str]:
    """Parse comma-separated CORS origins from settings."""

    origins = [item.strip() for item in settings.cors_allow_origins.split(",") if item.strip()]
    return origins or ["*"]
