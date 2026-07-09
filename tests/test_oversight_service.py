"""Tests for the oversight service (review queue, audit log)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import Review
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.oversight import ReviewCreate
from app.services.oversight_service import OversightService


@pytest.fixture
def mock_trace_repo():
    repo = AsyncMock(spec=TraceRepository)
    repo.list_recent.return_value = []
    return repo


@pytest.fixture
def mock_review_repo():
    return MagicMock(spec=ReviewRepository)


@pytest.fixture
def mock_audit_repo():
    return MagicMock(spec=AuditLogRepository)


@pytest.fixture
def service(mock_trace_repo, mock_review_repo, mock_audit_repo):
    return OversightService(mock_trace_repo, mock_review_repo, mock_audit_repo)


class TestOversightService:
    @pytest.mark.asyncio
    async def test_get_pending_reviews_empty(self, service):
        result = await service.get_pending_reviews()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_pending_reviews_filters_reviewed(self, service, mock_trace_repo, mock_review_repo):
        trace = MagicMock()
        trace.request_id = "req-001-x"
        trace.project_name = "test"
        trace.model_name = "gpt-4"
        trace.total_tokens = 100
        trace.cost = 0.01
        trace.prompt = "Hello"
        trace.response = "World"
        trace.flagged_for_governance = True
        trace.timestamp = datetime.now(timezone.utc)

        mock_trace_repo.list_flagged.return_value = [trace]
        mock_review_repo.get_latest_for_request.return_value = None

        result = await service.get_pending_reviews()
        assert len(result) == 1
        assert result[0].request_id == "req-001-x"

    @pytest.mark.asyncio
    async def test_create_review_adds_audit(self, service, mock_review_repo, mock_audit_repo):
        payload = ReviewCreate(request_id="req-001-long", reviewer="alice", decision="approved", notes="looks fine")

        mock_review = MagicMock(spec=Review)
        mock_review.id = 1
        mock_review.request_id = "req-001-x"
        mock_review.reviewer = "alice"
        mock_review.decision = "approved"
        mock_review.notes = "looks fine"
        mock_review.created_at = datetime.now(timezone.utc)

        mock_review_repo.create.return_value = mock_review

        result = await service.create_review(payload)
        assert result.decision == "approved"
        assert result.reviewer == "alice"
        mock_audit_repo.record.assert_called_once_with(
            actor="alice", action="review_create", resource_type="trace",
            resource_id="req-001-long", details={"decision": "approved", "notes": "looks fine"},
        )

    def test_get_audit_log(self, service, mock_audit_repo):
        mock_entry = MagicMock()
        mock_entry.id = 1
        mock_entry.actor = "alice"
        mock_entry.action = "policy_create"
        mock_entry.resource_type = "policy"
        mock_entry.resource_id = "42"
        mock_entry.details = {"name": "test-policy"}
        mock_entry.created_at = datetime.now(timezone.utc)

        mock_audit_repo.list_all.return_value = [mock_entry]

        result = service.get_audit_log()
        assert len(result) == 1
        assert result[0].actor == "alice"
        assert result[0].action == "policy_create"

    def test_get_reviews_for_trace(self, service, mock_review_repo):
        mock_review = MagicMock(spec=Review)
        mock_review.id = 1
        mock_review.request_id = "req-001-x"
        mock_review.reviewer = "bob"
        mock_review.decision = "rejected"
        mock_review.notes = "bad output"
        mock_review.created_at = datetime.now(timezone.utc)

        mock_review_repo.get_by_request_id.return_value = [mock_review]

        result = service.get_reviews_for_trace("req-001-x")
        assert len(result) == 1
        assert result[0].decision == "rejected"
        assert result[0].reviewer == "bob"

    @pytest.mark.asyncio
    async def test_get_reviewed_traces_only_shows_reviewed(self, service, mock_trace_repo, mock_review_repo):
        trace = MagicMock()
        trace.request_id = "req-002"
        trace.project_name = "test"
        trace.model_name = "gpt-4"
        trace.total_tokens = 50
        trace.cost = 0.005
        trace.prompt = "Hi"
        trace.response = "There"
        trace.flagged_for_governance = True
        trace.timestamp = datetime.now(timezone.utc)

        mock_trace_repo.list_flagged.return_value = [trace]

        mock_review = MagicMock(spec=Review)
        mock_review.id = 2
        mock_review.request_id = "req-002"
        mock_review.reviewer = "admin"
        mock_review.decision = "approved"
        mock_review.notes = None
        mock_review.created_at = datetime.now(timezone.utc)

        mock_review_repo.get_latest_for_request.return_value = mock_review

        result = await service.get_reviewed_traces()
        assert len(result) == 1
        assert result[0].request_id == "req-002"
        assert result[0].latest_review is not None
        assert result[0].latest_review.decision == "approved"
