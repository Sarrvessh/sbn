from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class TeamResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamProjectAssignRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")


class TeamProjectResponse(BaseModel):
    id: int
    team_id: int
    project_name: str

    model_config = ConfigDict(from_attributes=True)


class BudgetCreate(BaseModel):
    team_id: int = Field(gt=0)
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    budget_cents: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class BudgetUpdate(BaseModel):
    budget_cents: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class BudgetResponse(BaseModel):
    id: int
    team_id: int
    month: str
    budget_cents: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyCostPoint(BaseModel):
    date: str
    cost: float
    trace_count: int


class ModelCostBreakdown(BaseModel):
    model_name: str
    total_cost: float
    total_tokens: int
    trace_count: int


class ProjectCostBreakdown(BaseModel):
    project_name: str
    total_cost: float
    total_tokens: int
    trace_count: int


class CostAnalyticsResponse(BaseModel):
    total_cost: float
    total_tokens: int
    total_traces: int
    cost_this_month: float
    traces_this_month: int
    daily_costs: list[DailyCostPoint]
    by_model: list[ModelCostBreakdown]
    by_project: list[ProjectCostBreakdown]
    by_team: list[dict]


class PredictedCostPoint(BaseModel):
    date: str
    actual_cost: float | None = None
    predicted_cost: float | None = None


class CostPredictionResponse(BaseModel):
    projected_monthly_cost: float
    projected_daily_avg: float
    confidence: str  # "high", "medium", "low"
    daily_predictions: list[PredictedCostPoint]


class TeamCostSummary(BaseModel):
    team_id: int
    team_name: str
    total_cost: float
    total_tokens: int
    trace_count: int
    budget_cents: int | None
    budget_used_pct: float | None
