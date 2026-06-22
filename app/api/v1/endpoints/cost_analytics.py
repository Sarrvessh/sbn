from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.cost import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    CostAnalyticsResponse,
    CostPredictionResponse,
    PredictedCostPoint,
    TeamCostSummary,
    TeamCreate,
    TeamProjectAssignRequest,
    TeamProjectResponse,
    TeamResponse,
    TeamUpdate,
)
from app.services.cost_analytics_service import CostAnalyticsService

router = APIRouter(prefix="")


# Teams
@router.get("/teams", response_model=list[TeamResponse])
def list_teams(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[TeamResponse]:
    repo = TeamRepository(db)
    return [TeamResponse.model_validate(t) for t in repo.list_all()]


@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> TeamResponse:
    return TeamResponse.model_validate(TeamRepository(db).create(payload))


@router.get("/teams/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> TeamResponse:
    team = TeamRepository(db).get_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return TeamResponse.model_validate(team)


@router.put("/teams/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> TeamResponse:
    repo = TeamRepository(db)
    team = repo.update(team_id, payload)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return TeamResponse.model_validate(team)


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> None:
    repo = TeamRepository(db)
    if not repo.delete(team_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")


@router.post("/teams/{team_id}/projects", response_model=TeamProjectResponse, status_code=status.HTTP_201_CREATED)
def assign_project(
    team_id: int,
    payload: TeamProjectAssignRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> TeamProjectResponse:
    repo = TeamRepository(db)
    team = repo.get_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return TeamProjectResponse.model_validate(repo.assign_project(team_id, payload.project_name))


@router.delete("/teams/{team_id}/projects", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_project(
    team_id: int,
    project_name: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> None:
    repo = TeamRepository(db)
    if not repo.remove_project(team_id, project_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return None


@router.get("/teams/{team_id}/projects", response_model=list[TeamProjectResponse])
def list_team_projects(
    team_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[TeamProjectResponse]:
    repo = TeamRepository(db)
    return [TeamProjectResponse.model_validate(p) for p in repo.list_projects(team_id)]


# Budgets
@router.get("/budgets", response_model=list[BudgetResponse])
def list_budgets(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[BudgetResponse]:
    repo = BudgetRepository(db)
    return [BudgetResponse.model_validate(b) for b in repo.list_all()]


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> BudgetResponse:
    repo = BudgetRepository(db)
    existing = repo.get_for_team_month(payload.team_id, payload.month)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Budget already exists for this team/month",
        )
    return BudgetResponse.model_validate(repo.create(payload))


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> BudgetResponse:
    repo = BudgetRepository(db)
    budget = repo.update(budget_id, payload)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return BudgetResponse.model_validate(budget)


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> None:
    repo = BudgetRepository(db)
    if not repo.delete(budget_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")


# Cost Analytics
@router.get("/analytics/costs", response_model=CostAnalyticsResponse)
async def get_cost_analytics(
    project_name: str | None = Query(None),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("viewer", "analyst", "admin")),
) -> CostAnalyticsResponse:
    service = CostAnalyticsService(
        TraceRepository(), TeamRepository(db), BudgetRepository(db),
        audit_repo=AuditLogRepository(db),
    )
    project_names = [project_name] if project_name else None
    return await service.get_cost_analytics(project_names=project_names)


@router.get("/analytics/costs/teams", response_model=list[TeamCostSummary])
async def get_team_costs(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("viewer", "analyst", "admin")),
) -> list[TeamCostSummary]:
    service = CostAnalyticsService(
        TraceRepository(), TeamRepository(db), BudgetRepository(db),
        audit_repo=AuditLogRepository(db),
    )
    return await service.get_team_costs()


@router.get("/analytics/costs/predicted", response_model=CostPredictionResponse)
async def get_cost_prediction(
    project_name: str | None = Query(None),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("viewer", "analyst", "admin")),
) -> CostPredictionResponse:
    trace_repo = TraceRepository()
    project_names = [project_name] if project_name else None

    daily = await trace_repo.get_daily_costs(project_names=project_names)
    total_cost = await trace_repo.get_total_cost(project_names=project_names)
    total_traces = await trace_repo.get_trace_count(project_names=project_names)

    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    daily_map: dict[str, float] = {}
    for d in daily:
        daily_map[d["_id"]] = float(d["cost"])

    days_with_data = list(daily_map.keys())
    num_days = len(days_with_data)
    recent_daily_costs = [daily_map[d] for d in sorted(days_with_data)[-14:]]

    if num_days >= 7:
        recent_avg = sum(recent_daily_costs) / len(recent_daily_costs)
        confidence = "high" if num_days >= 14 else "medium"
    elif num_days >= 2:
        recent_avg = sum(recent_daily_costs) / len(recent_daily_costs)
        confidence = "low"
    else:
        recent_avg = total_cost / max(total_traces, 1) * 10
        confidence = "low"

    predictions: list[PredictedCostPoint] = []
    for i in range(14):
        date = (today - timedelta(days=13 - i)).strftime("%Y-%m-%d")
        actual = daily_map.get(date)
        pred = None
        if actual is None:
            pred = round(recent_avg, 6)
        predictions.append(PredictedCostPoint(date=date, actual_cost=actual, predicted_cost=pred))

    projected_monthly = round(recent_avg * 30, 6)

    return CostPredictionResponse(
        projected_monthly_cost=projected_monthly,
        projected_daily_avg=round(recent_avg, 6),
        confidence=confidence,
        daily_predictions=predictions,
    )
