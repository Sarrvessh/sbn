"""Tests for project repository."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.repositories.project_repository import ProjectRepository


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestProjectRepository:
    def test_create_and_get(self, db_session: Session) -> None:
        repo = ProjectRepository(db_session)
        from app.db.models import Project
        p = Project(name="test-project", description="A test project")
        created = repo.create(p)
        db_session.commit()
        assert created.id is not None
        assert created.name == "test-project"

        found = repo.get_by_name("test-project")
        assert found is not None
        assert found.description == "A test project"

    def test_get_or_create_returns_existing(self, db_session: Session) -> None:
        repo = ProjectRepository(db_session)
        p1 = repo.get_or_create_by_name("existing-project")
        db_session.commit()
        p2 = repo.get_or_create_by_name("existing-project")
        db_session.commit()
        assert p1.id == p2.id
        all_projects = repo.list_all()
        assert len(all_projects) == 1

    def test_get_or_create_creates_new(self, db_session: Session) -> None:
        repo = ProjectRepository(db_session)
        p = repo.get_or_create_by_name("brand-new-project")
        db_session.commit()
        assert p.name == "brand-new-project"
        assert repo.get_by_name("brand-new-project") is not None

    def test_delete_by_name(self, db_session: Session) -> None:
        repo = ProjectRepository(db_session)
        from app.db.models import Project
        repo.create(Project(name="delete-me"))
        db_session.commit()
        assert repo.delete_by_name("delete-me") is True
        assert repo.delete_by_name("delete-me") is False
        assert repo.get_by_name("delete-me") is None

    def test_list_all_empty(self, db_session: Session) -> None:
        repo = ProjectRepository(db_session)
        assert repo.list_all() == []

    def test_list_all_with_projects(self, db_session: Session) -> None:
        repo = ProjectRepository(db_session)
        from app.db.models import Project
        repo.create(Project(name="a"))
        repo.create(Project(name="b"))
        repo.create(Project(name="c"))
        db_session.commit()
        assert len(repo.list_all()) == 3

    def test_get_by_id(self, db_session: Session) -> None:
        repo = ProjectRepository(db_session)
        from app.db.models import Project
        p = repo.create(Project(name="by-id"))
        db_session.commit()
        found = repo.get_by_id(p.id)
        assert found is not None
        assert found.name == "by-id"
        assert repo.get_by_id(999) is None
