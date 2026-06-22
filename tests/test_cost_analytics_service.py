"""Tests for the cost analytics service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import Budget, Team, TeamProjectAssignment
from app.repositories.budget_repository import BudgetRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.cost import BudgetCreate, TeamCreate
from app.services.cost_analytics_service import CostAnalyticsService


@pytest.fixture
def mock_trace_repo():
    repo = AsyncMock(spec=TraceRepository)
    repo.get_total_cost.return_value = 0.0
    repo.get_total_tokens.return_value = 0
    repo.get_trace_count.return_value = 0
    repo.get_cost_this_month.return_value = 0.0
    repo.get_trace_count_this_month.return_value = 0
    repo.get_daily_costs.return_value = []
    repo.get_costs_by_model.return_value = []
    repo.get_costs_by_project.return_value = []
    repo.get_team_project_cost.return_value = (0.0, 0, 0)
    repo.get_team_project_cost_this_month.return_value = 0.0
    return repo


@pytest.fixture
def mock_team_repo():
    repo = MagicMock(spec=TeamRepository)
    repo.list_all.return_value = []
    repo.list_projects.return_value = []
    return repo


@pytest.fixture
def mock_budget_repo():
    repo = MagicMock(spec=BudgetRepository)
    repo.get_for_team_month.return_value = None
    return repo


@pytest.fixture
def service(mock_trace_repo, mock_team_repo, mock_budget_repo):
    return CostAnalyticsService(mock_trace_repo, mock_team_repo, mock_budget_repo)


class TestCostAnalyticsService:
    async def test_get_cost_analytics_empty(self, service):
        result = await service.get_cost_analytics()
        assert result.total_cost == 0.0
        assert result.total_tokens == 0
        assert result.total_traces == 0
        assert result.cost_this_month == 0.0
        assert result.traces_this_month == 0
        assert result.daily_costs == []
        assert result.by_model == []
        assert result.by_project == []

    async def test_get_cost_analytics_with_data(self, service, mock_trace_repo):
        mock_trace_repo.get_total_cost.return_value = 12.5
        mock_trace_repo.get_total_tokens.return_value = 700
        mock_trace_repo.get_trace_count.return_value = 5
        mock_trace_repo.get_cost_this_month.return_value = 8.0
        mock_trace_repo.get_trace_count_this_month.return_value = 3
        mock_trace_repo.get_daily_costs.return_value = [
            {"_id": "2026-06-01", "cost": 5.0, "cnt": 2},
            {"_id": "2026-06-02", "cost": 7.5, "cnt": 3},
        ]
        mock_trace_repo.get_costs_by_model.return_value = [
            {"_id": "gpt-4o", "cost": 10.0, "tokens": 500, "cnt": 3},
            {"_id": "gpt-4o-mini", "cost": 2.5, "tokens": 200, "cnt": 2},
        ]
        mock_trace_repo.get_costs_by_project.return_value = [
            {"_id": "proj-a", "cost": 8.0, "tokens": 400, "cnt": 3},
            {"_id": "proj-b", "cost": 4.5, "tokens": 300, "cnt": 2},
        ]

        result = await service.get_cost_analytics()
        assert result.total_cost == 12.5
        assert result.total_traces == 5
        assert len(result.daily_costs) == 2
        assert result.daily_costs[0].date == "2026-06-01"
        assert result.daily_costs[0].cost == 5.0
        assert len(result.by_model) == 2
        assert result.by_model[0].model_name == "gpt-4o"
        assert len(result.by_project) == 2
        assert result.by_project[0].project_name == "proj-a"

    async def test_get_team_costs_empty(self, service):
        result = await service.get_team_costs()
        assert result == []

    async def test_get_team_costs_with_budget(self, service, mock_trace_repo, mock_team_repo, mock_budget_repo):
        teams = [Team(id=1, name="Engineering", description=None)]
        assignments = [TeamProjectAssignment(id=1, team_id=1, project_name="proj-a")]
        budgets = [Budget(id=1, team_id=1, month="2026-06", budget_cents=10000)]

        mock_team_repo.list_all.return_value = teams
        mock_team_repo.list_projects.return_value = assignments
        mock_budget_repo.get_for_team_month.return_value = budgets[0]
        mock_trace_repo.get_team_project_cost.return_value = (0.0, 0, 0)

        result = await service.get_team_costs()
        assert len(result) == 1
        assert result[0].team_name == "Engineering"
        assert result[0].budget_cents == 10000
        assert result[0].budget_used_pct == 0.0


class TestTeamRepository:
    def test_create_team(self, db_session):
        repo = TeamRepository(db_session)
        payload = TeamCreate(name="Test Team", description="desc")
        team = repo.create(payload)
        assert team.name == "Test Team"


class TestBudgetRepository:
    def test_create_budget(self, db_session):
        repo = BudgetRepository(db_session)
        payload = BudgetCreate(team_id=1, month="2026-06", budget_cents=50000)
        budget = repo.create(payload)
        assert budget.team_id == 1
        assert budget.month == "2026-06"
