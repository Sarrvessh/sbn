from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Budget, Team
from app.schemas.cost import BudgetCreate, BudgetUpdate


class BudgetRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Budget]:
        stmt = select(Budget).order_by(Budget.month.desc(), Budget.team_id)
        return list(self._db.scalars(stmt).all())

    def get_by_id(self, budget_id: int) -> Budget | None:
        return self._db.get(Budget, budget_id)

    def get_for_team_month(self, team_id: int, month: str) -> Budget | None:
        stmt = select(Budget).where(
            Budget.team_id == team_id,
            Budget.month == month,
        )
        return self._db.scalar(stmt)

    def create(self, payload: BudgetCreate) -> Budget:
        if self._db.get(Team, payload.team_id) is None:
            raise ValueError(f"Team with id {payload.team_id} does not exist")
        budget = Budget(
            team_id=payload.team_id,
            month=payload.month,
            budget_cents=payload.budget_cents,
        )
        self._db.add(budget)
        self._db.commit()
        self._db.refresh(budget)
        return budget

    def update(self, budget_id: int, payload: BudgetUpdate) -> Budget | None:
        budget = self.get_by_id(budget_id)
        if budget is None:
            return None
        if payload.budget_cents is not None:
            budget.budget_cents = payload.budget_cents
        self._db.commit()
        self._db.refresh(budget)
        return budget

    def delete(self, budget_id: int) -> bool:
        budget = self.get_by_id(budget_id)
        if budget is None:
            return False
        self._db.delete(budget)
        self._db.commit()
        return True

    def list_for_team(self, team_id: int) -> list[Budget]:
        stmt = select(Budget).where(Budget.team_id == team_id).order_by(Budget.month.desc())
        return list(self._db.scalars(stmt).all())
