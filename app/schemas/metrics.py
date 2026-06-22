"""Schemas for metrics responses."""

from pydantic import BaseModel, Field


class MetricsResponse(BaseModel):
    """Aggregated telemetry metrics for dashboarding."""

    total_cost: float = Field(ge=0.0)
    average_latency_last_50_ms: float = Field(ge=0.0)
    governance_flagged_count: int = Field(ge=0)
