from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ActionType = Literal["flag", "block", "require_approval"]


class PolicyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    policy_type: Literal["regex", "keyword", "llm_judge", "pattern"]
    rule_config: dict[str, Any]
    severity: Literal["low", "medium", "high"] = "medium"
    enabled: bool = True
    action: ActionType = "flag"
    project_scope: str | None = None


class PolicyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    policy_type: Literal["regex", "keyword", "llm_judge", "pattern"] | None = None
    rule_config: dict[str, Any] | None = None
    severity: Literal["low", "medium", "high"] | None = None
    enabled: bool | None = None
    action: ActionType | None = None
    project_scope: str | None = None


class PolicyResponse(BaseModel):
    id: int
    name: str
    description: str | None
    policy_type: str
    rule_config: dict[str, Any]
    severity: str
    enabled: bool
    action: str = "flag"
    project_scope: str | None
    created_at: datetime
    updated_at: datetime


class PolicyTestRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)


class PolicyTestResult(BaseModel):
    policy_id: int
    policy_name: str
    matched: bool
    reason: str | None
    action: str = "flag"


class PolicyEvaluateResponse(BaseModel):
    decision: str
    matched_policies: list[PolicyTestResult]


class PolicyExceptionCreateRequest(BaseModel):
    policy_id: int = 0
    pattern: str = Field(min_length=1, max_length=500)
    reason: str | None = None


class PolicyExceptionResponse(BaseModel):
    id: int
    policy_id: int
    pattern: str
    reason: str | None
    created_at: datetime
