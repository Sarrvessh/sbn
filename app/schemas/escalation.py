from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EscalationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    rule_type: str = Field(min_length=1, max_length=30)
    rule_config: dict = Field(default_factory=dict)
    target_role: str = Field(min_length=1, max_length=20)

    model_config = ConfigDict(extra="forbid")


class EscalationRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    rule_type: str | None = None
    rule_config: dict | None = None
    target_role: str | None = None
    enabled: bool | None = None

    model_config = ConfigDict(extra="forbid")


class EscalationRuleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    rule_type: str
    rule_config: dict
    target_role: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
