from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Team, TeamProjectAssignment
from app.schemas.cost import TeamCreate, TeamUpdate


class TeamRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Team]:
        stmt = select(Team).order_by(Team.name)
        return list(self._db.scalars(stmt).all())

    def get_by_id(self, team_id: int) -> Team | None:
        return self._db.get(Team, team_id)

    def create(self, payload: TeamCreate) -> Team:
        team = Team(name=payload.name, description=payload.description)
        self._db.add(team)
        self._db.commit()
        self._db.refresh(team)
        return team

    def update(self, team_id: int, payload: TeamUpdate) -> Team | None:
        team = self.get_by_id(team_id)
        if team is None:
            return None
        if payload.name is not None:
            team.name = payload.name
        if payload.description is not None:
            team.description = payload.description
        self._db.commit()
        self._db.refresh(team)
        return team

    def delete(self, team_id: int) -> bool:
        team = self.get_by_id(team_id)
        if team is None:
            return False
        self._db.execute(
            delete(TeamProjectAssignment).where(TeamProjectAssignment.team_id == team_id)
        )
        self._db.delete(team)
        self._db.commit()
        return True

    def assign_project(self, team_id: int, project_name: str) -> TeamProjectAssignment:
        assignment = TeamProjectAssignment(team_id=team_id, project_name=project_name)
        self._db.add(assignment)
        self._db.commit()
        self._db.refresh(assignment)
        return assignment

    def remove_project(self, team_id: int, project_name: str) -> bool:
        stmt = delete(TeamProjectAssignment).where(
            TeamProjectAssignment.team_id == team_id,
            TeamProjectAssignment.project_name == project_name,
        )
        result = self._db.execute(stmt)
        self._db.commit()
        return result.rowcount > 0

    def list_projects(self, team_id: int) -> list[TeamProjectAssignment]:
        stmt = select(TeamProjectAssignment).where(
            TeamProjectAssignment.team_id == team_id
        ).order_by(TeamProjectAssignment.project_name)
        return list(self._db.scalars(stmt).all())

    def get_team_for_project(self, project_name: str) -> Team | None:
        stmt = select(TeamProjectAssignment).where(
            TeamProjectAssignment.project_name == project_name
        ).limit(1)
        assignment = self._db.scalar(stmt)
        if assignment is None:
            return None
        return self.get_by_id(assignment.team_id)
