"""Tests for alert rules repository."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.repositories.alert_rule_repository import AlertRuleRepository
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleUpdate


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestAlertRuleRepository:
    def test_create_and_list(self, db_session: Session) -> None:
        repo = AlertRuleRepository(db_session)
        rule = repo.create(AlertRuleCreate(
            name="High Latency Alert",
            alert_type="high_latency",
            threshold_value=2000.0,
            severity="high",
            enabled=True,
        ))
        assert rule.id is not None
        assert rule.name == "High Latency Alert"

        all_rules = repo.list_all()
        assert len(all_rules) == 1

    def test_project_specific_rule(self, db_session: Session) -> None:
        repo = AlertRuleRepository(db_session)
        repo.create(AlertRuleCreate(
            name="Global Latency",
            alert_type="high_latency",
            threshold_value=5000.0,
            severity="medium",
        ))
        repo.create(AlertRuleCreate(
            name="Project Latency",
            project_name="my-app",
            alert_type="high_latency",
            threshold_value=1000.0,
            severity="high",
        ))

        # Project-specific should return project rule first
        matching = repo.get_matching("my-app", "high_latency")
        assert len(matching) == 2
        assert matching[0].name == "Project Latency"  # project-specific first
        assert matching[0].threshold_value == 1000.0

        # Global query should only return global rules
        global_rules = repo.get_matching(None, "high_latency")
        assert len(global_rules) == 1
        assert global_rules[0].name == "Global Latency"

    def test_disabled_rule_not_matched(self, db_session: Session) -> None:
        repo = AlertRuleRepository(db_session)
        repo.create(AlertRuleCreate(
            name="Disabled Rule",
            alert_type="high_cost",
            threshold_value=0.1,
            enabled=False,
        ))
        matching = repo.get_matching(None, "high_cost")
        assert len(matching) == 0

    def test_update_rule(self, db_session: Session) -> None:
        repo = AlertRuleRepository(db_session)
        rule = repo.create(AlertRuleCreate(
            name="Old Name",
            alert_type="error_rate",
            threshold_value=5.0,
        ))
        updated = repo.update(rule.id, AlertRuleUpdate(name="New Name", threshold_value=10.0))
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.threshold_value == 10.0

    def test_delete_rule(self, db_session: Session) -> None:
        repo = AlertRuleRepository(db_session)
        rule = repo.create(AlertRuleCreate(
            name="Delete Me",
            alert_type="governance",
            threshold_value=1,
        ))
        assert repo.delete(rule.id) is True
        assert repo.delete(rule.id) is False

    def test_alert_type_filtering(self, db_session: Session) -> None:
        repo = AlertRuleRepository(db_session)
        repo.create(AlertRuleCreate(name="Latency", alert_type="high_latency", threshold_value=1000))
        repo.create(AlertRuleCreate(name="Cost", alert_type="high_cost", threshold_value=0.05))
        repo.create(AlertRuleCreate(name="Error", alert_type="error_rate", threshold_value=10))

        assert len(repo.get_matching(None, "high_latency")) == 1
        assert len(repo.get_matching(None, "high_cost")) == 1
        assert len(repo.get_matching(None, "error_rate")) == 1
        assert len(repo.get_matching(None, "governance")) == 0
