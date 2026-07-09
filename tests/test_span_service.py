"""Tests for span service and helper functions."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.span import SpanCreateRequest, SpanUpdateRequest
from app.services.span_service import SpanService, generate_span_id, generate_trace_id


class TestGenerateIds:
    def test_trace_id_length(self):
        assert len(generate_trace_id()) == 32

    def test_span_id_length(self):
        assert len(generate_span_id()) == 16

    def test_unique(self):
        assert generate_trace_id() != generate_trace_id()


def _make_span_embedded(**overrides):
    span = MagicMock()
    now = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    span.trace_id = overrides.get("trace_id", "trace-1")
    span.span_id = overrides.get("span_id", "span-1")
    span.parent_span_id = overrides.get("parent_span_id", None)
    span.trace_request_id = overrides.get("trace_request_id", "req-1")
    span.name = overrides.get("name", "test-span")
    span.kind = overrides.get("kind", "INTERNAL")
    span.span_type = overrides.get("span_type", "llm")
    span.input = overrides.get("input", "hello")
    span.output = overrides.get("output", "world")
    span.tool_name = overrides.get("tool_name", None)
    span.model_name = overrides.get("model_name", "gpt-4")
    span.input_tokens = overrides.get("input_tokens", 10)
    span.output_tokens = overrides.get("output_tokens", 20)
    span.total_tokens = overrides.get("total_tokens", 30)
    span.cost = overrides.get("cost", 0.001)
    span.attributes = overrides.get("attributes", None)
    span.retrieval_documents = overrides.get("retrieval_documents", None)
    span.status_code = overrides.get("status_code", "OK")
    span.status_message = overrides.get("status_message", None)
    span.started_at = overrides.get("started_at", now)
    span.ended_at = overrides.get("ended_at", now)
    span.created_at = overrides.get("created_at", now)
    return span


class TestSpanService:
    @pytest.mark.asyncio
    async def test_create_span(self):
        repo = MagicMock(spec=["create"])
        repo.create = AsyncMock(return_value=_make_span_embedded())
        svc = SpanService(repo)
        payload = SpanCreateRequest(
            trace_id="abcdef1234567890abcdef1234567890ab",
            span_id="span1234567890ab",
            trace_request_id="req-12345",
            name="test", span_type="llm", started_at=datetime.now(timezone.utc),
        )
        result = await svc.create_span(payload)
        assert result.span_id == "span-1"
        assert result.name == "test-span"

    @pytest.mark.asyncio
    async def test_update_span(self):
        repo = MagicMock(spec=["update"])
        repo.update = AsyncMock(return_value=_make_span_embedded(output="updated"))
        svc = SpanService(repo)
        payload = SpanUpdateRequest(output="updated")
        result = await svc.update_span("span-1", payload)
        assert result is not None
        assert result.span_id == "span-1"

    @pytest.mark.asyncio
    async def test_update_span_not_found(self):
        repo = MagicMock(spec=["update"])
        repo.update = AsyncMock(return_value=None)
        svc = SpanService(repo)
        payload = SpanUpdateRequest(output="updated")
        result = await svc.update_span("nonexistent", payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_spans_for_trace(self):
        repo = MagicMock(spec=["list_by_trace_request"])
        repo.list_by_trace_request = AsyncMock(return_value=[_make_span_embedded()])
        svc = SpanService(repo)
        spans = await svc.get_spans_for_trace("req-1")
        assert len(spans) == 1
        assert spans[0].span_id == "span-1"

    @pytest.mark.asyncio
    async def test_get_span_tree(self):
        now = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        parent = _make_span_embedded(span_id="parent", parent_span_id=None, trace_request_id="req-12345", started_at=now)
        child = _make_span_embedded(span_id="child", parent_span_id="parent", trace_request_id="req-12345", started_at=now)
        repo = MagicMock(spec=["list_by_trace_request"])
        repo.list_by_trace_request = AsyncMock(return_value=[parent, child])
        svc = SpanService(repo)
        tree = await svc.get_span_tree("req-12345")
        assert len(tree) == 1
        assert tree[0].span.span_id == "parent"
        assert len(tree[0].children) == 1

    @pytest.mark.asyncio
    async def test_record_root_span(self):
        repo = MagicMock(spec=["create"])
        repo.create = AsyncMock(return_value=_make_span_embedded())
        svc = SpanService(repo)
        result = await svc.record_root_span("req-12345", "abcdef1234567890abcdef1234567890ab", "root", "llm", model_name="gpt-4", input_text="hello")
        assert result.span_id == "span-1"

    @pytest.mark.asyncio
    async def test_finalize_span(self):
        repo = MagicMock(spec=["update"])
        repo.update = AsyncMock(return_value=_make_span_embedded(output="final"))
        svc = SpanService(repo)
        result = await svc.finalize_span("span-1", output="final", total_tokens=100, cost=0.01, status_code="OK")
        assert result is not None
        assert result.span_id == "span-1"