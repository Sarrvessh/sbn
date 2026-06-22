from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.cost import (
    CostAnalyticsResponse,
    DailyCostPoint,
    ModelCostBreakdown,
    ProjectCostBreakdown,
    TeamCostSummary,
)


class CostAnalyticsService:
    def __init__(
        self, trace_repository: TraceRepository, team_repo: TeamRepository,
        budget_repo: BudgetRepository,
        audit_repo: AuditLogRepository | None = None,
    ) -> None:
        self._trace_repo = trace_repository
        self._team_repo = team_repo
        self._budget_repo = budget_repo
        self._audit_repo = audit_repo

    async def get_cost_analytics(
        self, project_names: list[str] | None = None,
    ) -> CostAnalyticsResponse:
        now = datetime.now(timezone.utc)
        current_month = now.strftime("%Y-%m")

        total_cost = await self._trace_repo.get_total_cost(project_names)
        total_tokens = await self._trace_repo.get_total_tokens(project_names)
        total_traces = await self._trace_repo.get_trace_count(project_names)
        cost_this_month = await self._trace_repo.get_cost_this_month(project_names)
        traces_this_month = await self._trace_repo.get_trace_count_this_month(project_names)
        daily = await self._get_daily_costs(project_names)
        by_model = await self._get_by_model(project_names)
        by_project = await self._get_by_project(project_names)
        by_team = await self._get_by_team(project_names, current_month)

        return CostAnalyticsResponse(
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_traces=total_traces,
            cost_this_month=cost_this_month,
            traces_this_month=traces_this_month,
            daily_costs=daily,
            by_model=by_model,
            by_project=by_project,
            by_team=by_team,
        )

    async def get_team_costs(self) -> list[TeamCostSummary]:
        now = datetime.now(timezone.utc)
        current_month = now.strftime("%Y-%m")
        teams = self._team_repo.list_all()
        results: list[TeamCostSummary] = []

        for team in teams:
            projects = self._team_repo.list_projects(team.id)
            project_names = [p.project_name for p in projects]

            total_cost, total_tokens, trace_count = await self._trace_repo.get_team_project_cost(project_names)

            budget = self._budget_repo.get_for_team_month(team.id, current_month)
            budget_cents = budget.budget_cents if budget else None
            budget_used_pct = None
            if budget_cents and budget_cents > 0:
                cost_in_cents = int(total_cost * 100)
                budget_used_pct = round(min((cost_in_cents / budget_cents) * 100, 100), 1)

            results.append(TeamCostSummary(
                team_id=team.id,
                team_name=team.name,
                total_cost=total_cost,
                total_tokens=total_tokens,
                trace_count=trace_count,
                budget_cents=budget_cents,
                budget_used_pct=budget_used_pct,
            ))

            if (
                self._audit_repo is not None
                and budget_used_pct is not None
                and budget_used_pct >= settings.budget_alert_threshold_pct
            ):
                self._audit_repo.record(
                    actor="system",
                    action="budget_alert",
                    resource_type="budget",
                    resource_id=str(team.id),
                    details={
                        "team_name": team.name,
                        "budget_used_pct": budget_used_pct,
                        "budget_cents": budget_cents,
                        "threshold_pct": settings.budget_alert_threshold_pct,
                    },
                )

        return results

    async def _get_daily_costs(self, project_names: list[str] | None) -> list[DailyCostPoint]:
        rows = await self._trace_repo.get_daily_costs(project_names)
        return [
            DailyCostPoint(date=str(r["_id"]), cost=float(r["cost"]), trace_count=int(r["cnt"]))
            for r in rows
        ]

    async def _get_by_model(self, project_names: list[str] | None) -> list[ModelCostBreakdown]:
        rows = await self._trace_repo.get_costs_by_model(project_names)
        return [
            ModelCostBreakdown(
                model_name=str(r["_id"]),
                total_cost=float(r["cost"]),
                total_tokens=int(r["tokens"]),
                trace_count=int(r["cnt"]),
            )
            for r in rows
        ]

    async def _get_by_project(self, project_names: list[str] | None) -> list[ProjectCostBreakdown]:
        rows = await self._trace_repo.get_costs_by_project(project_names)
        return [
            ProjectCostBreakdown(
                project_name=str(r["_id"]),
                total_cost=float(r["cost"]),
                total_tokens=int(r["tokens"]),
                trace_count=int(r["cnt"]),
            )
            for r in rows
        ]

    async def _get_by_team(self, project_names: list[str] | None, current_month: str) -> list[dict]:
        teams = self._team_repo.list_all()
        result = []
        for team in teams:
            projects = self._team_repo.list_projects(team.id)
            team_projects = [p.project_name for p in projects]

            if project_names:
                team_projects = [p for p in team_projects if p in project_names]
            if not team_projects:
                continue

            total_cost, total_tokens, trace_count = await self._trace_repo.get_team_project_cost(team_projects)
            month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_cost = await self._trace_repo.get_team_project_cost_this_month(team_projects, month_start)

            budget = self._budget_repo.get_for_team_month(team.id, current_month)
            budget_used = None
            if budget and budget.budget_cents > 0:
                cost_cents = int(month_cost * 100)
                budget_used = round(min((cost_cents / budget.budget_cents) * 100, 100), 1)

            result.append({
                "team_id": team.id,
                "team_name": team.name,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "trace_count": trace_count,
                "month_cost": month_cost,
                "budget_cents": budget.budget_cents if budget else 0,
                "budget_used_pct": budget_used,
            })

        return result
