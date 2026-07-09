"""Data access layer for spans — PostgreSQL via SQLAlchemy."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable, TypeVar

from sqlalchemy.orm import Session

from app.db.models import Span, Trace
from app.db.session import SessionLocal
from app.schemas.span import SpanCreateRequest, SpanUpdateRequest
from app.services.governance_service import evaluate_governance

T = TypeVar("T")


class SpanRepository:
    def __init__(self, db: Session | None = None) -> None:
        self._db = db

    def _session(self) -> Session:
        if self._db is not None:
            return self._db
        return SessionLocal()

    def _cleanup(self, session: Session) -> None:
        if self._db is None:
            session.close()

    async def _run_async(self, fn: Callable[[], T]) -> T:
        if self._db is not None:
            return fn()
        return await asyncio.to_thread(fn)

    async def create(self, payload: SpanCreateRequest) -> Span:
        def _fn():
            session = self._session()
            try:
                span = Span(
                    span_id=payload.span_id,
                    parent_span_id=payload.parent_span_id,
                    trace_id=payload.trace_id,
                    trace_request_id=payload.trace_request_id,
                    project_name=payload.project_name,
                    name=payload.name,
                    kind=payload.kind,
                    span_type=payload.span_type,
                    input=payload.input,
                    output=payload.output,
                    tool_name=payload.tool_name,
                    model_name=payload.model_name,
                    input_tokens=payload.input_tokens,
                    output_tokens=payload.output_tokens,
                    total_tokens=payload.total_tokens,
                    cost=payload.cost,
                    attributes=payload.attributes,
                    status_code=payload.status_code,
                    status_message=payload.status_message,
                    started_at=payload.started_at,
                    ended_at=payload.ended_at,
                )
                session.add(span)
                trace = session.query(Trace).where(Trace.request_id == payload.trace_request_id).first()
                if trace is None:
                    trace = Trace(
                        request_id=payload.trace_request_id,
                        project_name=payload.project_name,
                        prompt="(auto-created from span)",
                        response="",
                        model_name=payload.model_name or "unknown",
                        total_tokens=0,
                        cost=0.0,
                        latency_ms=0.001,
                        status="success",
                        timestamp=payload.started_at or datetime.now(timezone.utc),
                    )
                    session.add(trace)
                session.flush()
                return span
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def update(self, span_id: str, payload: SpanUpdateRequest) -> Span | None:
        def _fn():
            session = self._session()
            try:
                span = session.query(Span).where(Span.span_id == span_id).first()
                if span is None:
                    return None
                if payload.output is not None:
                    span.output = payload.output
                if payload.output_tokens is not None:
                    span.output_tokens = payload.output_tokens
                if payload.total_tokens is not None:
                    span.total_tokens = payload.total_tokens
                if payload.cost is not None:
                    span.cost = payload.cost
                if payload.status_code is not None:
                    span.status_code = payload.status_code
                if payload.status_message is not None:
                    span.status_message = payload.status_message
                if payload.ended_at is not None:
                    span.ended_at = payload.ended_at
                if payload.attributes is not None:
                    span.attributes = payload.attributes
                session.flush()
                spans = session.query(Span).where(Span.trace_request_id == span.trace_request_id).all()
                trace = session.query(Trace).where(Trace.request_id == span.trace_request_id).first()
                if spans and trace:
                    agg_tokens = sum(s.total_tokens for s in spans)
                    agg_cost = sum(s.cost for s in spans)
                    times = [s.started_at for s in spans if s.started_at is not None]
                    if times:
                        max_end = max((s.ended_at or s.started_at) for s in spans if s.started_at is not None)
                        agg_latency = (max_end - min(times)).total_seconds() * 1000
                    else:
                        agg_latency = 0.001
                    trace.total_tokens = agg_tokens
                    trace.cost = agg_cost
                    trace.latency_ms = max(agg_latency, 0.001)
                    session.flush()
                if trace and not trace.flagged_for_governance:
                    span_text = " ".join(str(getattr(span, k, "") or "") for k in ("input", "output")).strip()
                    if span_text:
                        flagged, _ = evaluate_governance(span_text)
                        if flagged:
                            trace.flagged_for_governance = True
                            session.flush()
                return span
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def get_by_span_id(self, span_id: str) -> Span | None:
        def _fn():
            session = self._session()
            try:
                return session.query(Span).where(Span.span_id == span_id).first()
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def list_by_trace_request(self, trace_request_id: str) -> list[Span]:
        def _fn():
            session = self._session()
            try:
                return session.query(Span).where(Span.trace_request_id == trace_request_id).order_by(Span.started_at).all()
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)

    async def list_by_trace_id(self, trace_id: str) -> list[Span]:
        def _fn():
            session = self._session()
            try:
                return session.query(Span).where(Span.trace_id == trace_id).order_by(Span.started_at).all()
            finally:
                self._cleanup(session)
        return await self._run_async(_fn)
