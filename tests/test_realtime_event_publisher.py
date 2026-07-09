"""Tests for realtime event publishing after trace ingestion."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.realtime_event_publisher import _safe_preview, publish_trace_update_event


class TestSafePreview:
    def test_short_text_unchanged(self):
        assert _safe_preview("hello world") == "hello world"

    def test_long_text_truncated(self):
        text = "a " * 200
        result = _safe_preview(text)
        assert len(result) <= 180

    def test_normalized_whitespace(self):
        assert _safe_preview("hello   world") == "hello world"

    def test_exact_max_length(self):
        text = "x" * 180
        assert _safe_preview(text) == text


class TestPublishTraceUpdateEvent:
    @pytest.mark.asyncio
    async def test_publishes_event(self):
        trace = MagicMock()
        trace.project_name = "test-project"
        trace.request_id = "req-123"
        trace.model_name = "gpt-4"
        trace.total_tokens = 100
        trace.cost = 0.002
        trace.latency_ms = 500
        trace.status = "success"
        trace.flagged_for_governance = False
        trace.prompt = "hello"
        trace.response = "world"
        trace.timestamp = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        repository = MagicMock()
        db = MagicMock()

        with patch("app.services.realtime_event_publisher.RealtimeAnalyzerService") as MockAnalyzer:
            analyzer = MagicMock()
            analyzer.get_realtime_metrics = AsyncMock(return_value=MagicMock(model_dump=lambda **kw: {"total_cost": 10.0}))
            analyzer.get_alerts = AsyncMock(return_value=[])
            MockAnalyzer.return_value = analyzer

            with patch("app.services.realtime_event_publisher.event_stream_service") as mock_ess:
                await publish_trace_update_event(trace, repository, db)

        mock_ess.publish.assert_called_once()
        event = mock_ess.publish.call_args[0][0]
        assert event["event_type"] == "trace_ingested"
        assert event["project_name"] == "test-project"
        assert event["trace"]["request_id"] == "req-123"
        assert "metrics" in event
        assert "alerts" in event