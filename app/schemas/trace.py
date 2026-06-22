"""Schemas for trace ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.span import SpanResponse


class TraceIngestRequest(BaseModel):
    """Incoming telemetry payload from SDK."""

    request_id: str = Field(min_length=8, max_length=64)
    project_name: str = Field(min_length=1, max_length=255)
    prompt: str = Field(min_length=1)
    response: str = Field(min_length=0)
    model_name: str = Field(min_length=1, max_length=255)
    total_tokens: int = Field(default=0, ge=0)
    cost: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(gt=0.0)
    status: Literal["success", "error"]
    flagged_for_governance: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


class IngestResponse(BaseModel):
    """Acknowledgement for accepted traces."""

    request_id: str
    message: str = "Trace ingested successfully"


class TraceDetailResponse(BaseModel):
    """Full trace detail for single-trace inspection."""

    request_id: str
    project_name: str
    prompt: str
    response: str
    model_name: str
    total_tokens: int
    cost: float
    latency_ms: float
    status: Literal["success", "error"]
    flagged_for_governance: bool
    timestamp: datetime
    spans: list[SpanResponse] = []
