from __future__ import annotations

import pytest

from app.services.cache_service import metrics_cache
from app.services.realtime_analyzer_service import RealtimeAnalyzerService


class TestRealtimeAnalyzerService:
    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        metrics_cache.clear()
    @pytest.mark.asyncio
    async def test_empty_db_returns_zeros(self, trace_repository):
        service = RealtimeAnalyzerService(trace_repository)
        metrics = await service.get_realtime_metrics(window_size=50)
        assert metrics.total_cost == 0.0
        assert metrics.average_latency_last_50_ms == 0.0
        assert metrics.p95_latency_last_50_ms == 0.0
        assert metrics.governance_flagged_count == 0
        assert metrics.error_rate_last_50_percent == 0.0
        assert metrics.traces_last_24h == 0

    @pytest.mark.asyncio
    async def test_recent_traces(self, trace_repository, seeded_traces):
        service = RealtimeAnalyzerService(trace_repository)
        traces = await service.get_recent_traces(limit=5)
        assert len(traces) <= 5
        assert all(t.project_name == "test-project" for t in traces)

    @pytest.mark.asyncio
    async def test_recent_traces_filtered_by_project(self, trace_repository, seeded_traces):
        service = RealtimeAnalyzerService(trace_repository)
        traces = await service.get_recent_traces(limit=100, project_names=["other-project"])
        assert len(traces) == 0

    @pytest.mark.asyncio
    async def test_metrics_with_data(self, trace_repository, seeded_traces):
        service = RealtimeAnalyzerService(trace_repository)
        metrics = await service.get_realtime_metrics(window_size=50)
        assert metrics.total_cost > 0.0
        assert metrics.traces_last_24h == 20

    @pytest.mark.asyncio
    async def test_alerts_generated(self, trace_repository, seeded_traces):
        service = RealtimeAnalyzerService(trace_repository)
        alerts = await service.get_alerts(limit=50)
        error_alerts = [a for a in alerts if a.alert_type == "execution_error"]
        assert len(error_alerts) > 0
