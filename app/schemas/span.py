from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RetrievalDocumentSchema(BaseModel):
    id: str
    content: str
    score: float | None = None
    source: str | None = None


class SpanCreateRequest(BaseModel):
    trace_id: str = Field(min_length=32, max_length=64)
    span_id: str = Field(min_length=16, max_length=32)
    parent_span_id: str | None = None
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
    retrieval_documents: list[RetrievalDocumentSchema] | None = None
    status_code: str = "UNSET"
    status_message: str | None = None
    started_at: datetime
    ended_at: datetime | None = None


class SpanUpdateRequest(BaseModel):
    output: str | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    status_code: str | None = None
    status_message: str | None = None
    ended_at: datetime | None = None
    attributes: dict[str, Any] | None = None
    retrieval_documents: list[RetrievalDocumentSchema] | None = None


class SpanResponse(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None
    trace_request_id: str
    name: str
    kind: str
    span_type: str
    input: str | None
    output: str | None
    tool_name: str | None
    model_name: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    attributes: dict[str, Any] | None
    retrieval_documents: list[RetrievalDocumentSchema] | None = None
    status_code: str
    status_message: str | None
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime


class SpanTreeResponse(BaseModel):
    """A span with its children nested for waterfall display."""

    span: SpanResponse
    children: list[SpanTreeResponse]
    duration_ms: float
