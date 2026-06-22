from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WebhookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=1024)
    secret: str | None = None
    events: list[str] = Field(default_factory=list)
    enabled: bool = True

    model_config = ConfigDict(extra="forbid")


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    secret: str | None = None
    events: list[str] | None = None
    enabled: bool | None = None

    model_config = ConfigDict(extra="forbid")


class WebhookResponse(BaseModel):
    id: int
    name: str
    url: str
    secret: str | None
    events: list[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookDeliveryResponse(BaseModel):
    id: int
    webhook_id: int
    event_type: str
    payload: dict
    status: str
    status_code: int | None
    response_body: str | None
    delivered_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookTestRequest(BaseModel):
    url: str = Field(min_length=1, max_length=1024)
    secret: str | None = None


class WebhookTestResponse(BaseModel):
    success: bool
    status_code: int | None
    response_body: str | None
    error: str | None = None
