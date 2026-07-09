"""Tests for trace repository — uses SQLite in-memory."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.repositories.trace_repository import TraceRepository
from app.schemas.trace import TraceIngestRequest


class TestGetAverageLatencyLastN:
    @pytest.mark.asyncio
    async def test_empty_returns_zero(self, trace_repository: TraceRepository):
        result = await trace_repository.get_average_latency_last_n(10)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_with_traces(self, trace_repository: TraceRepository):
        now = datetime.now(timezone.utc)
        repo = trace_repository
        for i in range(5):
            payload = TraceIngestRequest(
                request_id=f"latency-req-{i}",
                project_name="test",
                prompt="test",
                response="",
                model_name="gpt-4",
                total_tokens=10,
                cost=0.001,
                latency_ms=100.0 + i * 50.0,
                status="success",
                timestamp=now + timedelta(seconds=i),
            )
            await repo.create(payload)
        result = await repo.get_average_latency_last_n(10)
        assert result == 200.0


class TestGetGovernanceFlaggedCount:
    @pytest.mark.asyncio
    async def test_count(self, trace_repository: TraceRepository):
        repo = trace_repository
        now = datetime.now(timezone.utc)
        for i in range(10):
            payload = TraceIngestRequest(
                request_id=f"gov-req-{i}",
                project_name="test",
                prompt="test",
                response="",
                model_name="gpt-4",
                total_tokens=10,
                cost=0.001,
                latency_ms=100.0,
                status="success",
                flagged_for_governance=(i < 3),
                timestamp=now,
            )
            await repo.create(payload)
        result = await repo.get_governance_flagged_count()
        assert result == 3


class TestGetErrorRateLastN:
    @pytest.mark.asyncio
    async def test_no_traces(self, trace_repository: TraceRepository):
        result = await trace_repository.get_error_rate_last_n(50)
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_some_errors(self, trace_repository: TraceRepository):
        repo = trace_repository
        now = datetime.now(timezone.utc)
        for i in range(10):
            payload = TraceIngestRequest(
                request_id=f"err-req-{i}",
                project_name="test",
                prompt="test",
                response="",
                model_name="gpt-4",
                total_tokens=10,
                cost=0.001,
                latency_ms=100.0,
                status="error" if i < 4 else "success",
                timestamp=now + timedelta(seconds=i),
            )
            await repo.create(payload)
        result = await repo.get_error_rate_last_n(50)
        assert result == 40.0


class TestGetProjectStats:
    @pytest.mark.asyncio
    async def test_empty(self, trace_repository: TraceRepository):
        stats = await trace_repository.get_project_stats("nonexistent")
        assert stats["total_tokens"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["total_traces"] == 0
        assert stats["models"] == []

    @pytest.mark.asyncio
    async def test_with_data(self, trace_repository: TraceRepository):
        repo = trace_repository
        now = datetime.now(timezone.utc)
        for i in range(10):
            payload = TraceIngestRequest(
                request_id=f"stats-req-{i}",
                project_name="stats-proj",
                prompt="test",
                response="",
                model_name="gpt-4",
                total_tokens=100 + i * 10,
                cost=0.5 + i * 0.1,
                latency_ms=200.0,
                status="success" if i < 8 else "error",
                timestamp=now,
            )
            await repo.create(payload)
        stats = await repo.get_project_stats("stats-proj")
        assert stats["total_traces"] == 10
        assert stats["total_cost"] > 0
        assert stats["total_tokens"] > 0


class TestDeleteByProject:
    @pytest.mark.asyncio
    async def test_delete(self, trace_repository: TraceRepository):
        repo = trace_repository
        now = datetime.now(timezone.utc)
        for i in range(5):
            payload = TraceIngestRequest(
                request_id=f"del-req-{i}",
                project_name="delete-me",
                prompt="test",
                response="",
                model_name="gpt-4",
                total_tokens=10,
                cost=0.001,
                latency_ms=100.0,
                status="success",
                timestamp=now,
            )
            await repo.create(payload)
        count = await repo.delete_by_project("delete-me")
        assert count == 5
        remaining = await repo.get_trace_count()
        assert remaining == 0
