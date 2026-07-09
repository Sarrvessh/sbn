from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.db.models import Span
from app.repositories.span_repository import SpanRepository
from app.schemas.span import (
    SpanCreateRequest,
    SpanResponse,
    SpanTreeResponse,
    SpanUpdateRequest,
)


def generate_trace_id() -> str:
    return uuid4().hex[:32]


def generate_span_id() -> str:
    return uuid4().hex[:16]


def _span_to_response(span: Span) -> SpanResponse:
    return SpanResponse(
        trace_id=span.trace_id,
        span_id=span.span_id,
        parent_span_id=span.parent_span_id,
        trace_request_id=span.trace_request_id,
        name=span.name,
        kind=span.kind,
        span_type=span.span_type,
        input=span.input,
        output=span.output,
        tool_name=span.tool_name,
        model_name=span.model_name,
        input_tokens=span.input_tokens,
        output_tokens=span.output_tokens,
        total_tokens=span.total_tokens,
        cost=span.cost,
        attributes=span.attributes,
        retrieval_documents=span.retrieval_documents,
        status_code=span.status_code,
        status_message=span.status_message,
        started_at=span.started_at,
        ended_at=span.ended_at,
        created_at=span.created_at,
    )


class SpanService:
    def __init__(self, span_repository: SpanRepository) -> None:
        self._repository = span_repository

    async def create_span(self, payload: SpanCreateRequest) -> SpanResponse:
        span = await self._repository.create(payload)
        return _span_to_response(span)

    async def update_span(self, span_id: str, payload: SpanUpdateRequest) -> SpanResponse | None:
        span = await self._repository.update(span_id, payload)
        if span is None:
            return None
        return _span_to_response(span)

    async def get_spans_for_trace(self, trace_request_id: str) -> list[SpanResponse]:
        spans = await self._repository.list_by_trace_request(trace_request_id)
        return [_span_to_response(s) for s in spans]

    async def get_span_tree(self, trace_request_id: str) -> list[SpanTreeResponse]:
        spans = await self._repository.list_by_trace_request(trace_request_id)
        span_map: dict[str, SpanTreeResponse] = {}
        roots: list[SpanTreeResponse] = []

        for s in spans:
            resp = _span_to_response(s)
            duration = ((s.ended_at or s.started_at) - s.started_at).total_seconds() * 1000
            tree = SpanTreeResponse(span=resp, children=[], duration_ms=max(duration, 0.01))
            span_map[s.span_id] = tree

        for s in spans:
            tree = span_map[s.span_id]
            if s.parent_span_id and s.parent_span_id in span_map:
                span_map[s.parent_span_id].children.append(tree)
            else:
                roots.append(tree)

        return roots

    async def record_root_span(
        self,
        trace_request_id: str,
        trace_id: str,
        name: str,
        span_type: str,
        model_name: str | None = None,
        input_text: str | None = None,
    ) -> SpanResponse:
        now = datetime.now(timezone.utc)
        payload = SpanCreateRequest(
            trace_id=trace_id,
            span_id=generate_span_id(),
            parent_span_id=None,
            trace_request_id=trace_request_id,
            name=name,
            kind="INTERNAL",
            span_type=span_type,
            input=input_text,
            model_name=model_name,
            started_at=now,
            ended_at=now,
            status_code="UNSET",
        )
        return await self.create_span(payload)

    async def finalize_span(
        self,
        span_id: str,
        output: str | None = None,
        total_tokens: int = 0,
        cost: float = 0.0,
        status_code: str = "OK",
        status_message: str | None = None,
    ) -> SpanResponse | None:
        update = SpanUpdateRequest(
            output=output,
            total_tokens=total_tokens,
            cost=cost,
            status_code=status_code,
            status_message=status_message,
            ended_at=datetime.now(timezone.utc),
        )
        return await self.update_span(span_id, update)
