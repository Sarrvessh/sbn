"""Integration tests requiring a running backend and MySQL."""

from __future__ import annotations

import os

import pytest
import requests

BACKEND_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("SBN_API_KEY", "admin-local-dev-key")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def backend_available():
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def test_health_endpoint(backend_available):
    if not backend_available:
        pytest.skip("Backend not available")
    resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_agent_run_and_trace_persisted(backend_available):
    if not backend_available:
        pytest.skip("Backend not available")

    run_payload = {
        "project_name": "integration-test",
        "prompt": "Say hello in one word",
        "model_name": "gpt-4o-mini",
        "max_tokens": 50,
        "temperature": 0.0,
    }
    run_resp = requests.post(
        f"{BACKEND_URL}/api/v1/agent/run",
        json=run_payload,
        headers={"X-API-Key": API_KEY},
        timeout=60,
    )
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["status"] == "success"
    assert data["request_id"] is not None

    request_id = data["request_id"]

    recent_resp = requests.get(
        f"{BACKEND_URL}/api/v1/traces/recent?limit=50",
        headers={"X-API-Key": API_KEY},
        timeout=10,
    )
    assert recent_resp.status_code == 200
    traces = recent_resp.json()
    matching = [t for t in traces if t["request_id"] == request_id]
    assert len(matching) == 1

    metrics_resp = requests.get(
        f"{BACKEND_URL}/api/v1/analytics/realtime",
        headers={"X-API-Key": API_KEY},
        timeout=10,
    )
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["total_cost"] >= 0
    assert metrics["traces_last_24h"] >= 1


def test_unauthorized_access(backend_available):
    if not backend_available:
        pytest.skip("Backend not available")
    resp = requests.get(
        f"{BACKEND_URL}/api/v1/analytics/realtime",
        timeout=5,
    )
    assert resp.status_code == 401


def test_ingest_endpoint(backend_available):
    if not backend_available:
        pytest.skip("Backend not available")
    payload = {
        "request_id": "int-test-ingest-001",
        "project_name": "integration-test",
        "prompt": "Test ingest",
        "response": "OK",
        "model_name": "gpt-4o-mini",
        "total_tokens": 10,
        "cost": 0.001,
        "latency_ms": 100.0,
        "status": "success",
        "flagged_for_governance": False,
    }
    resp = requests.post(
        f"{BACKEND_URL}/api/v1/ingest",
        json=payload,
        headers={"X-API-Key": API_KEY},
        timeout=10,
    )
    assert resp.status_code == 201
    assert resp.json()["request_id"] == "int-test-ingest-001"
