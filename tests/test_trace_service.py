from __future__ import annotations

import pytest

from app.services.trace_service import TraceService


class TestTraceService:
    @pytest.mark.asyncio
    async def test_ingest_trace(self, trace_repository, sample_trace_payload):
        service = TraceService(trace_repository)
        trace = await service.ingest_trace(sample_trace_payload)
        assert trace.request_id == "test-req-001"
        assert trace.project_name == "test-project"
        assert trace.status == "success"
        assert trace.total_tokens == 50

    @pytest.mark.asyncio
    async def test_ingest_and_retrieve(self, trace_repository, sample_trace_payload):
        service = TraceService(trace_repository)
        await service.ingest_trace(sample_trace_payload)

        traces = await trace_repository.list_recent(limit=10)
        assert len(traces) == 1
        assert traces[0].request_id == "test-req-001"

    @pytest.mark.asyncio
    async def test_get_metrics_empty(self, trace_repository):
        service = TraceService(trace_repository)
        metrics = await service.get_metrics(window_size=50)
        assert metrics.total_cost == 0.0
        assert metrics.average_latency_last_50_ms == 0.0
        assert metrics.governance_flagged_count == 0

    @pytest.mark.asyncio
    async def test_get_metrics_with_data(self, trace_repository, seeded_traces):
        service = TraceService(trace_repository)
        metrics = await service.get_metrics(window_size=50)
        assert metrics.total_cost > 0.0
        assert metrics.average_latency_last_50_ms > 0.0
