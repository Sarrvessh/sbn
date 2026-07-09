"""Tests for webhook delivery logic (retry, signature, fan-out)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.webhook_service import (
    _compute_signature,
    deliver_event,
    deliver_webhook,
)
from app.services.webhook_service import test_webhook_delivery as _test_webhook_svc


class TestComputeSignature:
    def test_signature_computed(self):
        sig = _compute_signature("secret", b'{"key":"value"}')
        assert isinstance(sig, str)
        assert len(sig) == 64

    def test_different_secret_different_sig(self):
        s1 = _compute_signature("secret1", b"body")
        s2 = _compute_signature("secret2", b"body")
        assert s1 != s2

    def test_different_body_different_sig(self):
        s1 = _compute_signature("secret", b"body1")
        s2 = _compute_signature("secret", b"body2")
        assert s1 != s2


class MockResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self._text = text
        self.is_success = 200 <= status_code < 300

    @property
    def text(self) -> str:
        return self._text


class TestDeliverWebhook:
    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        wh = MagicMock()
        wh.id = 1
        wh.secret = "secret"
        wh.url = "http://example.com/hook"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MockResponse(200, "ok")
            result = await deliver_webhook(wh, "trace_ingested", {"key": "val"})

        assert result["status"] == "success"
        assert result["status_code"] == 200
        assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_5xx(self):
        wh = MagicMock()
        wh.id = 1
        wh.secret = "secret"
        wh.url = "http://example.com/hook"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MockResponse(500)
            result = await deliver_webhook(wh, "trace_ingested", {"key": "val"})

        assert result["status"] == "fail"
        assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_on_4xx(self):
        wh = MagicMock()
        wh.id = 1
        wh.secret = "secret"
        wh.url = "http://example.com/hook"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MockResponse(400)
            result = await deliver_webhook(wh, "trace_ingested", {"key": "val"})

        assert result["status"] == "fail"
        assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self):
        wh = MagicMock()
        wh.id = 1
        wh.secret = "secret"
        wh.url = "http://example.com/hook"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            from httpx import TimeoutException
            mock_post.side_effect = TimeoutException("timeout")
            result = await deliver_webhook(wh, "trace_ingested", {"key": "val"})

        assert result["status"] == "fail"
        assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_includes_signature_header(self):
        wh = MagicMock()
        wh.id = 1
        wh.secret = "mysecret"
        wh.url = "http://example.com/hook"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MockResponse(200, "ok")
            await deliver_webhook(wh, "trace_ingested", {"key": "val"})

        _call_headers = mock_post.call_args[1]["headers"]
        assert "X-SBN-Signature" in _call_headers
        assert "X-SBN-Event" in _call_headers
        assert _call_headers["X-SBN-Event"] == "trace_ingested"


class TestDeliverEvent:
    @pytest.mark.asyncio
    async def test_no_webhooks_returns_empty(self):
        db = MagicMock()
        repo = MagicMock()
        repo.get_enabled_by_events.return_value = []
        with patch("app.services.webhook_service.WebhookRepository", return_value=repo):
            results = await deliver_event("trace_ingested", {"key": "val"}, db)
        assert results == []

    @pytest.mark.asyncio
    async def test_fans_out_to_multiple_webhooks(self):
        db = MagicMock()
        wh1 = MagicMock(id=1, secret="s1", url="http://a.com")
        wh2 = MagicMock(id=2, secret="s2", url="http://b.com")
        repo = MagicMock()
        repo.get_enabled_by_events.return_value = [wh1, wh2]
        repo.log_delivery.return_value = None

        with patch("app.services.webhook_service.WebhookRepository", return_value=repo):
            with patch("app.services.webhook_service.deliver_webhook", new_callable=AsyncMock) as mock_deliver:
                mock_deliver.return_value = {
                    "webhook_id": 1, "event_type": "trace_ingested",
                    "status": "success", "status_code": 200,
                }
                results = await deliver_event("trace_ingested", {"key": "val"}, db)

        assert len(results) == 2
        assert repo.log_delivery.call_count == 2


class TestTestWebhook:
    @pytest.mark.asyncio
    async def test_success(self):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MockResponse(200, "ok")
            result = await _test_webhook_svc("http://example.com/hook", "secret")
        assert result["success"] is True
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_no_secret(self):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MockResponse(200, "ok")
            result = await _test_webhook_svc("http://example.com/hook", None)
        assert result["success"] is True
