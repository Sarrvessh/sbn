"""Schemas for realtime analytics and alerting APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RealtimeMetricsResponse(BaseModel):
    """High-signal metrics for realtime observability dashboards."""

    total_cost: float = Field(ge=0.0)
    average_latency_last_50_ms: float = Field(ge=0.0)
    p95_latency_last_50_ms: float = Field(ge=0.0)
    governance_flagged_count: int = Field(ge=0)
    error_rate_last_50_percent: float = Field(ge=0.0)
    traces_last_24h: int = Field(ge=0)


class RecentTraceResponse(BaseModel):
    """Trace row representation optimized for dashboard views."""

    request_id: str
    project_name: str
    model_name: str
    total_tokens: int
    cost: float
    latency_ms: float
    status: Literal["success", "error"]
    flagged_for_governance: bool
    prompt_preview: str
    response_preview: str
    timestamp: datetime


class GovernanceMetricsResponse(BaseModel):
    total_traces: int
    total_flagged: int
    flag_rate: float
    pending_reviews: int
    approved_reviews: int
    rejected_reviews: int
    by_severity: list[dict] = Field(default_factory=list)
    recent_flags: list[dict] = Field(default_factory=list)


class SystemMetricsResponse(BaseModel):
    total_traces: int
    total_projects: int
    error_rate: float
    average_latency_ms: float
    total_tokens: int
    total_cost: float
    unique_models: list[str]
    traces_today: int
    uptime_hours: float = 0.0


class AlertResponse(BaseModel):
    """Detected operational or governance alert from recent traces."""

    request_id: str
    project_name: str
    severity: Literal["low", "medium", "high"]
    alert_type: Literal["high_latency", "high_cost", "governance", "execution_error"]
    message: str
    latency_ms: float
    cost: float
    status: Literal["success", "error"]
    timestamp: datetime
