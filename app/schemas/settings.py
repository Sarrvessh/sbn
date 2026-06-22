from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AppSettingsResponse(BaseModel):
    default_agent_model: str = "gpt-4o-mini"
    max_tokens: int = 1024
    temperature: float = 0.2
    sampling_rate: int = 100
    budget_alert_threshold_pct: float = 80.0
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_referer: str | None = None
    openai_app_title: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def model_validate(cls, obj: object, *args, **kwargs) -> AppSettingsResponse:
        result = super().model_validate(obj, *args, **kwargs)
        if result.openai_api_key:
            k = result.openai_api_key
            result.openai_api_key = k[:4] + "••••" + k[-4:] if len(k) > 8 else "••••"
        return result


class AppSettingsUpdate(BaseModel):
    default_agent_model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    sampling_rate: int | None = None
    budget_alert_threshold_pct: float | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_referer: str | None = None
    openai_app_title: str | None = None

    model_config = ConfigDict(extra="forbid")
