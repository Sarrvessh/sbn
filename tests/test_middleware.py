"""Tests for request timing middleware."""
from __future__ import annotations

import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.testclient import TestClient

from app.main import app
from app.services.metrics_service import registry


@pytest.fixture(autouse=True)
def _clear_metrics():
    for c in registry._counters.values():
        c._values.clear()
    for h in registry._histograms.values():
        h._values.clear()
    yield


class TestRequestTimingMiddleware:
    def test_response_has_timing_header(self):
        client = TestClient(app)
        resp = client.get("/api/v1/projects")
        assert "X-Response-Time-Ms" in resp.headers

    def test_metrics_path_excluded(self):
        client = TestClient(app)
        resp = client.get("/metrics")
        assert "X-Response-Time-Ms" not in resp.headers

    def test_increments_http_requests_total(self):
        client = TestClient(app)
        client.get("/api/v1/projects")
        output = registry.collect_all()
        assert "http_requests_total" in output
        assert 'method="GET"' in output

    def test_records_http_request_duration(self):
        client = TestClient(app)
        client.get("/api/v1/projects")
        output = registry.collect_all()
        assert "http_request_duration_seconds" in output