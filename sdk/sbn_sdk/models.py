"""SDK models for telemetry payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TracePayload(BaseModel):
    """Outbound telemetry payload sent from SDK to backend."""

    request_id: str = Field(min_length=8, max_length=64)
    project_name: str = Field(min_length=1, max_length=255)
    prompt: str = Field(default="")
    response: str = Field(default="")
    model_name: str = Field(default="unknown", min_length=1, max_length=255)
    total_tokens: int = Field(default=0, ge=0)
    cost: float = Field(default=0.0, ge=0.0)
    latency_ms: float = Field(gt=0.0)
    status: Literal["success", "error"]
    flagged_for_governance: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")


class SpanPayload(BaseModel):
    """Outbound span creation payload sent from SDK to backend."""

    trace_id: str = Field(min_length=32, max_length=64)
    span_id: str = Field(min_length=16, max_length=32)
    parent_span_id: str | None = None
    trace_request_id: str = Field(min_length=8, max_length=64)
    project_name: str = Field(default="default", min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    kind: str = "INTERNAL"
    span_type: str = Field(min_length=1, max_length=30)
    input: str = ""
    output: str = ""
    tool_name: str = ""
    model_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    status_code: str = "UNSET"
    status_message: str = ""
    started_at: datetime
    ended_at: datetime | None = None
    latency_ms: float = 0.0

    model_config = ConfigDict(extra="forbid")
