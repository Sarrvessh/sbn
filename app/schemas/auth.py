"""Schemas for API key administration."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreateRequest(BaseModel):
    """Request payload for creating a new API key."""

    role: Literal["admin", "analyst", "viewer", "ingest"]
    project_scope: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


class ApiKeyInfoResponse(BaseModel):
    """Metadata representation for stored API keys."""

    key_prefix: str
    role: str
    project_scope: str | None
    description: str | None
    is_active: bool
    created_at: datetime


class ApiKeyCreateResponse(ApiKeyInfoResponse):
    """Create response that includes the raw API key once."""

    api_key: str
