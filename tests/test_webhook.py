"""Tests for webhook retry logic."""

from __future__ import annotations

from app.services.webhook_service import _is_retryable


class TestWebhookRetry:
    def test_timeout_is_retryable(self):
        assert _is_retryable({"status_code": None}) is True

    def test_connection_error_is_retryable(self):
        assert _is_retryable({"status_code": None, "response_body": "Connection refused"}) is True

    def test_5xx_is_retryable(self):
        assert _is_retryable({"status_code": 500}) is True
        assert _is_retryable({"status_code": 502}) is True
        assert _is_retryable({"status_code": 503}) is True

    def test_4xx_is_not_retryable(self):
        assert _is_retryable({"status_code": 400}) is False
        assert _is_retryable({"status_code": 401}) is False
        assert _is_retryable({"status_code": 403}) is False
        assert _is_retryable({"status_code": 404}) is False

    def test_success_is_not_retryable(self):
        assert _is_retryable({"status_code": 200}) is False

    def test_3xx_is_not_retryable(self):
        assert _is_retryable({"status_code": 301}) is False
        assert _is_retryable({"status_code": 302}) is False
