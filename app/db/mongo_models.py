"""Beanie document models for MongoDB (traces with embedded spans)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field


class RetrievalDocument(BaseModel):
    id: str
    content: str
    score: float | None = None
    source: str | None = None


class SpanEmbedded(BaseModel):
    span_id: str = Field(min_length=16, max_length=32)
    parent_span_id: str | None = None
    trace_id: str = Field(min_length=32, max_length=64)
    trace_request_id: str = Field(min_length=8, max_length=64)
    project_name: str = Field(default="default", min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    kind: str = "INTERNAL"
    span_type: str = Field(min_length=1, max_length=30)
    input: str | None = None
    output: str | None = None
    tool_name: str | None = None
    model_name: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    attributes: dict[str, Any] | None = None
    retrieval_documents: list[RetrievalDocument] | None = None
    status_code: str = "UNSET"
    status_message: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TraceDocument(Document):
    request_id: str = Field(min_length=8, max_length=64)
    project_name: str = Field(min_length=1, max_length=255)
    prompt: str = Field(min_length=1)
    response: str = Field(min_length=0)
    model_name: str = Field(min_length=1, max_length=255)
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: float
    status: str = Field(pattern=r"^(success|error)$")
    flagged_for_governance: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    spans: list[SpanEmbedded] = Field(default_factory=list)

    class Settings:
        name = "traces"
        indexes = [
            "request_id",
            "project_name",
            "status",
            "timestamp",
            [("project_name", 1), ("timestamp", -1)],
            [("spans.span_id", 1)],
        ]
