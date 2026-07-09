"""Base utilities for framework integrations."""
from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter

from sbn_sdk.client import get_or_create_client
from sbn_sdk.models import SpanPayload

logger = logging.getLogger(__name__)


def generate_span_id() -> str:
    return uuid.uuid4().hex[:16]


def generate_trace_id() -> str:
    return uuid.uuid4().hex[:32]


class IntegrationSpan:
    """Lightweight span for use inside framework integrations."""

    def __init__(
        self,
        backend_url: str,
        api_key: str | None,
        trace_request_id: str,
        trace_id: str,
        span_id: str,
        parent_span_id: str | None,
        name: str,
        span_type: str = "integration",
        input_text: str | None = None,
        tool_name: str | None = None,
        model_name: str | None = None,
        project_name: str = "default",
    ) -> None:
        self._client = get_or_create_client(backend_url, api_key=api_key)
        self._trace_request_id = trace_request_id
        self._trace_id = trace_id
        self._span_id = span_id
        self._parent_span_id = parent_span_id
        self._started_at = datetime.now(timezone.utc)
        self._start_perf = perf_counter()
        self._name = name
        self._span_type = span_type
        self._tool_name = tool_name or ""
        self._model_name = model_name or ""
        self._project_name = project_name
        self._input_tokens = 0
        self._output_tokens = 0
        self._total_tokens = 0
        self._cost = 0.0
        self._output = ""
        self._status_code = "UNSET"
        self._status_message = ""

        self._client.send_span_non_blocking(
            SpanPayload(
                trace_id=self._trace_id,
                span_id=self._span_id,
                parent_span_id=self._parent_span_id,
                trace_request_id=self._trace_request_id,
                project_name=self._project_name,
                name=self._name,
                span_type=self._span_type,
                input=input_text or "",
                tool_name=self._tool_name,
                model_name=self._model_name,
                started_at=self._started_at,
            )
        )

    def end(
        self,
        output: str = "",
        status_code: str = "OK",
        status_message: str = "",
        total_tokens: int = 0,
        cost: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        elapsed = (perf_counter() - self._start_perf) * 1000
        ended_at = datetime.now(timezone.utc)
        self._client.send_span_finalize_non_blocking(
            span_id=self._span_id,
            output=output or self._output,
            total_tokens=total_tokens or self._total_tokens,
            cost=cost or self._cost,
            status_code=status_code or self._status_code,
            status_message=status_message or self._status_message,
            started_at=self._started_at,
            ended_at=ended_at,
            latency_ms=elapsed,
        )

    def end_error(self, message: str) -> None:
        self.end(output=message, status_code="ERROR", status_message=message)


class IntegrationTracer:
    """Shared tracer state for framework integrations."""

    def __init__(
        self,
        backend_url: str,
        api_key: str | None = None,
        trace_request_id: str | None = None,
        trace_id: str | None = None,
        project_name: str = "default",
        model_name: str = "unknown",
        sampling_rate: float = 1.0,
    ) -> None:
        self._backend_url = backend_url
        self._api_key = api_key
        self.trace_request_id = trace_request_id or generate_trace_id()[:32]
        self.trace_id = trace_id or generate_trace_id()
        self.project_name = project_name
        self.model_name = model_name
        self.sampling_rate = max(0.0, min(1.0, sampling_rate))
        self._span_stack: list[str] = []
        self._stack_lock = Lock()

    @property
    def current_parent_span_id(self) -> str | None:
        with self._stack_lock:
            return self._span_stack[-1] if self._span_stack else None

    def create_span(
        self,
        name: str,
        span_type: str = "integration",
        input_text: str | None = None,
        tool_name: str | None = None,
        model_name: str | None = None,
    ) -> IntegrationSpan | None:
        if random.random() >= self.sampling_rate:
            return None
        span_id = generate_span_id()
        parent_id = self.current_parent_span_id
        span = IntegrationSpan(
            backend_url=self._backend_url,
            api_key=self._api_key,
            trace_request_id=self.trace_request_id,
            trace_id=self.trace_id,
            span_id=span_id,
            parent_span_id=parent_id,
            name=name,
            span_type=span_type,
            input_text=input_text,
            tool_name=tool_name,
            model_name=model_name or self.model_name,
            project_name=self.project_name,
        )
        with self._stack_lock:
            self._span_stack.append(span_id)
        return span

    def end_span(self, span: IntegrationSpan) -> None:
        if span is None:
            return
        with self._stack_lock:
            if span._span_id in self._span_stack:
                self._span_stack.remove(span._span_id)
        span.end()
