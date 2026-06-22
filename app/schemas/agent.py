"""Schemas for live agent execution endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentRunRequest(BaseModel):
    """Request payload for running a real LLM call through backend."""

    project_name: str = Field(min_length=1, max_length=255)
    prompt: str = Field(min_length=1, max_length=8000)
    model_name: str = Field(default="gpt-4o-mini", min_length=1, max_length=255)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)

    model_config = ConfigDict(extra="forbid")


class AgentRunResponse(BaseModel):
    """Result payload for one live agent execution."""

    request_id: str
    project_name: str
    status: Literal["success", "error"]
    model_name: str
    response: str
    total_tokens: int = Field(ge=0)
    cost: float = Field(ge=0.0)
    latency_ms: float = Field(ge=0.0)
    flagged_for_governance: bool
    governance_reasons: list[str]
    timestamp: datetime
