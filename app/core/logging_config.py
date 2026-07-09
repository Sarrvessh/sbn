"""Structured JSON logging configuration with request context support."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "request_id"):
            entry["request_id"] = record.request_id

        if hasattr(record, "extra"):
            for k, v in record.extra.items():
                entry[k] = v
        return json.dumps(entry, default=str)


def configure_logging(*, json_format: bool | None = None) -> None:
    if json_format is None:
        json_format = os.environ.get("SBN_JSON_LOG", "").lower() in ("1", "true", "yes")

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        ))

    root.handlers.clear()
    root.addHandler(handler)
