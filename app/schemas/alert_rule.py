from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    project_name: str | None = None
    alert_type: str = Field(min_length=1, max_length=30)
    severity: str = Field(default="medium", max_length=10)
    threshold_value: float = Field(ge=0.0)
    enabled: bool = True

    model_config = ConfigDict(extra="forbid")


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    project_name: str | None = None
    alert_type: str | None = None
    severity: str | None = None
    threshold_value: float | None = None
    enabled: bool | None = None

    model_config = ConfigDict(extra="forbid")


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    project_name: str | None
    alert_type: str
    severity: str
    threshold_value: float
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
