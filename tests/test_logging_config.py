"""Tests for JSON logging configuration."""
from __future__ import annotations

import json
import logging

from app.core.logging_config import JSONFormatter, configure_logging


class TestJSONFormatter:
    def test_format_creates_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "hello world"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["module"] == "test"
        assert parsed["line"] == 10

    def test_includes_exception(self):
        formatter = JSONFormatter()
        try:
            1 / 0
        except ZeroDivisionError:
            import sys
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=20,
                msg="boom",
                args=(),
                exc_info=exc_info,
            )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ZeroDivisionError" in parsed["exception"]

    def test_includes_extra(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=5,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.__dict__["extra"] = {"trace_id": "abc"}
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["trace_id"] == "abc"


class TestConfigureLogging:
    def test_configure_with_json(self, monkeypatch):
        monkeypatch.delenv("SBN_JSON_LOG", raising=False)
        configure_logging(json_format=True)
        root = logging.getLogger()
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)

    def test_configure_with_text(self, monkeypatch):
        monkeypatch.delenv("SBN_JSON_LOG", raising=False)
        configure_logging(json_format=False)
        root = logging.getLogger()
        handler = root.handlers[0]
        assert not isinstance(handler.formatter, JSONFormatter)

    def test_configure_from_env(self, monkeypatch):
        monkeypatch.setenv("SBN_JSON_LOG", "true")
        configure_logging(json_format=None)
        root = logging.getLogger()
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)
