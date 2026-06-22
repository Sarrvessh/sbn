from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Project


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Project]:
        return self.db.query(Project).order_by(Project.name).all()

    def get_by_name(self, name: str) -> Project | None:
        return self.db.query(Project).filter(Project.name == name).first()

    def get_by_id(self, project_id: int) -> Project | None:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def get_or_create_by_name(self, name: str) -> Project:
        existing = self.get_by_name(name)
        if existing:
            return existing
        project = Project(name=name)
        self.db.add(project)
        self.db.flush()
        return project

    def create(self, project: Project) -> Project:
        self.db.add(project)
        self.db.flush()
        return project

    def delete_by_name(self, name: str) -> bool:
        project = self.get_by_name(name)
        if project is None:
            return False
        self.db.delete(project)
        self.db.flush()
        return True
