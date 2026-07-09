"""Tests for SDK data models."""

from __future__ import annotations

from datetime import datetime, timezone

from sbn_sdk.models import SpanPayload, TracePayload


class TestTracePayload:
    def test_valid_payload(self):
        payload = TracePayload(
            request_id="req123456",
            project_name="test",
            prompt="Hello",
            response="World",
            model_name="gpt-4",
            total_tokens=10,
            cost=0.001,
            latency_ms=100.0,
            status="success",
            timestamp=datetime.now(timezone.utc),
        )
        data = payload.model_dump(mode="json")
        assert data["request_id"] == "req123456"
        assert data["status"] == "success"

    def test_default_values(self):
        payload = TracePayload(
            request_id="req123456",
            project_name="test",
            prompt="Hi",
            response="Bye",
            model_name="gpt-3",
            total_tokens=5,
            cost=0.0005,
            latency_ms=50.0,
            status="success",
            timestamp=datetime.now(timezone.utc),
        )
        assert payload.flagged_for_governance is False

    def test_flagged_trace(self):
        payload = TracePayload(
            request_id="req123456",
            project_name="test",
            prompt="Hi",
            response="Bye",
            model_name="gpt-3",
            total_tokens=5,
            cost=0.0005,
            latency_ms=50.0,
            status="success",
            flagged_for_governance=True,
            timestamp=datetime.now(timezone.utc),
        )
        assert payload.flagged_for_governance is True


class TestSpanPayload:
    def test_valid_payload(self):
        now = datetime.now(timezone.utc)
        payload = SpanPayload(
            trace_id="t" * 32,
            span_id="s" * 16,
            parent_span_id=None,
            trace_request_id="req123456",
            project_name="test",
            name="test-span",
            span_type="llm",
            input="hello",
            output="world",
            total_tokens=10,
            cost=0.001,
            started_at=now,
        )
        data = payload.model_dump(mode="json", exclude_none=True)
        assert data["name"] == "test-span"

    def test_default_status_code(self):
        now = datetime.now(timezone.utc)
        payload = SpanPayload(
            trace_id="t" * 32,
            span_id="s" * 16,
            trace_request_id="req123456",
            project_name="test",
            name="test",
            span_type="llm",
            total_tokens=0,
            cost=0.0,
            started_at=now,
        )
        assert payload.status_code == "UNSET"
