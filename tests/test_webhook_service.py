"""Tests for webhook delivery and repository."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import Webhook
from app.repositories.webhook_repository import WebhookRepository
from app.schemas.webhook import WebhookCreate, WebhookUpdate


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestWebhookRepository:
    def test_create_and_list(self, db_session: Session) -> None:
        repo = WebhookRepository(db_session)
        payload = WebhookCreate(
            name="test-webhook",
            url="https://hooks.example.com/alert",
            events=["alert.high_latency", "alert.execution_error"],
            enabled=True,
        )
        wh = repo.create(payload)
        assert wh.id is not None
        assert wh.name == "test-webhook"
        assert wh.url == "https://hooks.example.com/alert"

        all_wh = repo.list_all()
        assert len(all_wh) == 1

    def test_update_webhook(self, db_session: Session) -> None:
        repo = WebhookRepository(db_session)
        wh = repo.create(WebhookCreate(name="wh1", url="https://example.com/1", events=["alert.governance"]))
        updated = repo.update(wh.id, WebhookUpdate(name="wh1-updated", enabled=False))
        assert updated is not None
        assert updated.name == "wh1-updated"
        assert updated.enabled is False

    def test_delete_webhook(self, db_session: Session) -> None:
        repo = WebhookRepository(db_session)
        wh = repo.create(WebhookCreate(name="wh-del", url="https://example.com/del", events=[]))
        assert repo.delete(wh.id) is True
        assert repo.delete(wh.id) is False
        assert len(repo.list_all()) == 0

    def test_get_by_id_returns_none_for_missing(self, db_session: Session) -> None:
        repo = WebhookRepository(db_session)
        assert repo.get_by_id(999) is None

    def test_delivery_logging(self, db_session: Session) -> None:
        repo = WebhookRepository(db_session)
        wh = repo.create(WebhookCreate(name="wh-delivery", url="https://example.com/dlv", events=[]))
        repo.log_delivery(
            webhook_id=wh.id,
            event_type="alert.high_cost",
            payload={"cost": 0.5},
            status="success",
            status_code=200,
            response_body="OK",
        )
        deliveries = repo.list_deliveries(wh.id, limit=10)
        assert len(deliveries) == 1
        assert deliveries[0].status == "success"
        assert deliveries[0].event_type == "alert.high_cost"

    def test_delivery_logging_failure(self, db_session: Session) -> None:
        repo = WebhookRepository(db_session)
        wh = repo.create(WebhookCreate(name="wh-fail", url="https://example.com/fail", events=[]))
        repo.log_delivery(
            webhook_id=wh.id,
            event_type="alert.execution_error",
            payload={"error": "timeout"},
            status="fail",
            status_code=500,
            response_body="Internal Server Error",
        )
        deliveries = repo.list_deliveries(wh.id, limit=10)
        assert len(deliveries) == 1
        assert deliveries[0].status == "fail"

    def test_create_with_secret(self, db_session: Session) -> None:
        repo = WebhookRepository(db_session)
        wh = repo.create(WebhookCreate(
            name="wh-secret",
            url="https://example.com/sec",
            secret="my-super-secret-123",
            events=["alert.high_latency"],
        ))
        assert wh.id is not None
        assert repo.get_by_id(wh.id) is not None
