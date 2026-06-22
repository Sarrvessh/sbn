"""Data access layer for spans — embedded documents in MongoDB traces."""

from __future__ import annotations

from datetime import datetime, timezone

from app.db.mongo_models import SpanEmbedded, TraceDocument
from app.schemas.span import SpanCreateRequest, SpanUpdateRequest
from app.services.governance_service import evaluate_governance


class SpanRepository:
    async def create(self, payload: SpanCreateRequest) -> SpanEmbedded:
        span = SpanEmbedded(
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
            retrieval_documents=payload.retrieval_documents,
            status_code=payload.status_code,
            status_message=payload.status_message,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
        )
        trace = await TraceDocument.find_one({"request_id": payload.trace_request_id})
        if trace is None:
            trace = TraceDocument(
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
                spans=[],
            )
            await trace.insert()
        trace.spans.append(span)
        await trace.save()
        return span

    async def update(self, span_id: str, payload: SpanUpdateRequest) -> SpanEmbedded | None:
        update_fields = {}
        if payload.output is not None:
            update_fields["spans.$.output"] = payload.output
        if payload.output_tokens is not None:
            update_fields["spans.$.output_tokens"] = payload.output_tokens
        if payload.total_tokens is not None:
            update_fields["spans.$.total_tokens"] = payload.total_tokens
        if payload.cost is not None:
            update_fields["spans.$.cost"] = payload.cost
        if payload.status_code is not None:
            update_fields["spans.$.status_code"] = payload.status_code
        if payload.status_message is not None:
            update_fields["spans.$.status_message"] = payload.status_message
        if payload.ended_at is not None:
            update_fields["spans.$.ended_at"] = payload.ended_at
        if payload.attributes is not None:
            update_fields["spans.$.attributes"] = payload.attributes
        if payload.retrieval_documents is not None:
            update_fields["spans.$.retrieval_documents"] = [
                d.model_dump() for d in payload.retrieval_documents
            ]

        if not update_fields:
            return await self.get_by_span_id(span_id)

        collection = TraceDocument.get_motor_collection()
        result = await collection.find_one_and_update(
            {"spans.span_id": span_id},
            {"$set": update_fields},
            return_document=True,
        )
        if result is None:
            return None

        # Recompute parent TraceDocument aggregate fields from all spans
        spans_data = result.get("spans", [])
        agg_tokens = sum(s.get("total_tokens", 0) or 0 for s in spans_data)
        agg_cost = sum(s.get("cost", 0.0) or 0.0 for s in spans_data)
        times = [
            s["started_at"]
            for s in spans_data
            if s.get("started_at") is not None
        ]
        if times:
            agg_latency = (
                max(
                    s.get("ended_at") or s["started_at"]
                    for s in spans_data
                    if s.get("started_at") is not None
                ) - min(times)
            ).total_seconds() * 1000
        else:
            agg_latency = 0.001
        await collection.update_one(
            {"spans.span_id": span_id},
            {
                "$set": {
                    "total_tokens": agg_tokens,
                    "cost": agg_cost,
                    "latency_ms": max(agg_latency, 0.001),
                }
            },
        )

        # Auto-flag parent trace for governance if span text contains PII/violations
        updated_span = next((s for s in spans_data if s.get("span_id") == span_id), None)
        if updated_span and not result.get("flagged_for_governance"):
            span_text = " ".join(
                str(updated_span.get(k, "") or "") for k in ("input", "output")
            ).strip()
            if span_text:
                flagged, _ = evaluate_governance(span_text)
                if flagged:
                    await collection.update_one(
                        {"_id": result["_id"]},
                        {"$set": {"flagged_for_governance": True}},
                    )

        for span in spans_data:
            if span.get("span_id") == span_id:
                return SpanEmbedded(**span)
        return None

    async def get_by_span_id(self, span_id: str) -> SpanEmbedded | None:
        trace = await TraceDocument.find_one({"spans.span_id": span_id})
        if trace is None:
            return None
        for span in trace.spans:
            if span.span_id == span_id:
                return span
        return None

    async def list_by_trace_request(self, trace_request_id: str) -> list[SpanEmbedded]:
        trace = await TraceDocument.find_one({"request_id": trace_request_id})
        if trace is None:
            return []
        return sorted(trace.spans, key=lambda s: s.started_at)

    async def list_by_trace_id(self, trace_id: str) -> list[SpanEmbedded]:
        trace = await TraceDocument.find_one({"spans.trace_id": trace_id})
        if trace is None:
            return []
        matching = [s for s in trace.spans if s.trace_id == trace_id]
        return sorted(matching, key=lambda s: s.started_at)
