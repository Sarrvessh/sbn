from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    total_tokens: int = 0
    total_traces: int = 0
    models_used: list[str] = []


class ProjectDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    total_tokens: int
    total_cost: float
    total_traces: int
    success_rate: float
    average_latency_ms: float
    models_used: list[str]
    first_trace_at: datetime | None


class ProjectCreateRequest(BaseModel):
    name: str
    description: str | None = None
