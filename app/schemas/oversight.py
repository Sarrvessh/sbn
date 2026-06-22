from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)
    reviewer: str = Field(min_length=1, max_length=255)
    decision: Literal["approved", "rejected", "needs_revision"]
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class ReviewResponse(BaseModel):
    id: int
    request_id: str
    reviewer: str
    decision: str
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PendingReviewItem(BaseModel):
    request_id: str
    project_name: str
    model_name: str
    total_tokens: int
    cost: float
    prompt_preview: str
    response_preview: str
    timestamp: datetime
    latest_review: ReviewResponse | None


class AuditLogResponse(BaseModel):
    id: int
    actor: str
    action: str
    resource_type: str
    resource_id: str | None
    details: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
