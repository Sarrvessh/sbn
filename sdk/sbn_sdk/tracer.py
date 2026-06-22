from __future__ import annotations

import random
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from typing import Any, Generator

from sbn_sdk.client import get_or_create_client
from sbn_sdk.models import SpanPayload


def _generate_trace_id() -> str:
    return uuid.uuid4().hex[:32]


def _generate_span_id() -> str:
    return uuid.uuid4().hex[:16]


class SbnTracer:
    """Create and manage spans within a trace."""

    def __init__(
        self,
        backend_url: str,
        api_key: str | None = None,
        trace_request_id: str | None = None,
        trace_id: str | None = None,
        project_name: str = "default",
        sampling_rate: float = 1.0,
    ) -> None:
        self._backend_url = backend_url
        self._api_key = api_key
        self._client = get_or_create_client(backend_url, api_key=api_key)
        self.sampling_rate = max(0.0, min(1.0, sampling_rate))
        self._project_name = project_name

        self.trace_id = trace_id or _generate_trace_id()
        self.trace_request_id = trace_request_id or uuid.uuid4().hex
        self._span_stack: list[str] = []
        self._stack_lock = Lock()

    @property
    def current_parent_span_id(self) -> str | None:
        with self._stack_lock:
            return self._span_stack[-1] if self._span_stack else None

    @contextmanager
    def span(
        self,
        name: str,
        span_type: str = "llm",
        model_name: str | None = None,
        tool_name: str | None = None,
        input_text: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[_Span | None, None, None]:
        if random.random() >= self.sampling_rate:
            yield None
            return

        span_id = _generate_span_id()
        parent_id = self.current_parent_span_id
        started_at = datetime.now(timezone.utc)
        start_perf = perf_counter()

        # Send create request
        self._client.send_span_non_blocking(
            SpanPayload(
                trace_id=self.trace_id,
                span_id=span_id,
                parent_span_id=parent_id,
                trace_request_id=self.trace_request_id,
                project_name=self._project_name,
                name=name,
                span_type=span_type,
                input=input_text or "",
                tool_name=tool_name or "",
                model_name=model_name or "",
                started_at=started_at,
            )
        )

        with self._stack_lock:
            self._span_stack.append(span_id)
        span_context = _Span(
            tracer=self,
            span_id=span_id,
            started_at=started_at,
            start_perf=start_perf,
        )

        try:
            yield span_context
        except Exception as exc:
            with self._stack_lock:
                self._span_stack.remove(span_id)
            span_context._end(
                output=str(exc),
                status_code="ERROR",
                status_message=str(exc),
            )
            raise
        else:
            with self._stack_lock:
                self._span_stack.remove(span_id)
            span_context._end()

    def _finalize_span(
        self,
        span_id: str,
        output: str,
        total_tokens: int,
        cost: float,
        status_code: str,
        status_message: str | None,
        started_at: datetime,
        start_perf: float,
    ) -> None:
        elapsed = (perf_counter() - start_perf) * 1000
        ended_at = datetime.now(timezone.utc)

        self._client.send_span_finalize_non_blocking(
            span_id=span_id,
            output=output,
            total_tokens=total_tokens,
            cost=cost,
            status_code=status_code,
            status_message=status_message or "",
            started_at=started_at,
            ended_at=ended_at,
            latency_ms=elapsed,
        )


class _Span:
    """Context manager result for an active span."""

    def __init__(
        self,
        tracer: SbnTracer,
        span_id: str,
        started_at: datetime,
        start_perf: float,
    ) -> None:
        self._tracer = tracer
        self._span_id = span_id
        self._started_at = started_at
        self._start_perf = start_perf
        self._output: str = ""
        self._total_tokens: int = 0
        self._cost: float = 0.0
        self._status_code: str = "OK"
        self._status_message: str | None = None

    def set_output(
        self,
        output: str,
        total_tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        self._output = output
        self._total_tokens = total_tokens
        self._cost = cost

    def set_error(self, message: str) -> None:
        self._status_code = "ERROR"
        self._status_message = message

    def _end(
        self,
        output: str | None = None,
        status_code: str | None = None,
        status_message: str | None = None,
    ) -> None:
        if output is not None:
            self._output = output
        if status_code is not None:
            self._status_code = status_code
        if status_message is not None:
            self._status_message = status_message

        self._tracer._finalize_span(
            span_id=self._span_id,
            output=self._output,
            total_tokens=self._total_tokens,
            cost=self._cost,
            status_code=self._status_code,
            status_message=self._status_message,
            started_at=self._started_at,
            start_perf=self._start_perf,
        )
