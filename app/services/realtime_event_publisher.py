"""Helpers for publishing enriched realtime events after trace ingestion."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.mongo_models import TraceDocument
from app.repositories.trace_repository import TraceRepository
from app.services.event_stream_service import event_stream_service
from app.services.realtime_analyzer_service import RealtimeAnalyzerService


async def publish_trace_update_event(trace: TraceDocument, repository: TraceRepository, db: Session | None = None) -> None:
    analyzer = RealtimeAnalyzerService(repository)
    project_name = trace.project_name

    metrics = await analyzer.get_realtime_metrics(
        window_size=settings.metrics_window_size,
        project_names=[project_name],
    )
    recent_alerts = await analyzer.get_alerts(limit=20, project_names=[project_name], db=db)
    matching_alerts = [
        alert.model_dump(mode="json")
        for alert in recent_alerts
        if alert.request_id == trace.request_id
    ]

    event_stream_service.publish({
        "event_type": "trace_ingested",
        "project_name": project_name,
        "trace": {
            "request_id": trace.request_id,
            "project_name": trace.project_name,
            "model_name": trace.model_name,
            "total_tokens": trace.total_tokens,
            "cost": trace.cost,
            "latency_ms": trace.latency_ms,
            "status": trace.status,
            "flagged_for_governance": trace.flagged_for_governance,
            "prompt_preview": _safe_preview(trace.prompt),
            "response_preview": _safe_preview(trace.response),
            "timestamp": trace.timestamp.isoformat(),
        },
        "metrics": metrics.model_dump(mode="json"),
        "alerts": matching_alerts,
        "timestamp": trace.timestamp.isoformat(),
    })


def _safe_preview(value: str, max_chars: int = 180) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3] + "..."
