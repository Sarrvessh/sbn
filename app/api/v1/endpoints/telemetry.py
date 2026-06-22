"""HTTP endpoints for telemetry ingest and metrics retrieval — async with MongoDB."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    Principal,
    require_roles,
    resolve_project_scope,
    resolve_project_scopes,
)
from app.db.session import get_db
from app.repositories.project_repository import ProjectRepository
from app.repositories.span_repository import SpanRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.metrics import MetricsResponse
from app.schemas.trace import IngestResponse, TraceIngestRequest
from app.services.governance_service import evaluate_governance
from app.services.realtime_event_publisher import publish_trace_update_event
from app.services.span_service import SpanService
from app.services.trace_service import TraceService

router = APIRouter(prefix="")


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_trace(
    payload: TraceIngestRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("ingest", "analyst")),
) -> IngestResponse:
    resolve_project_scope(principal, payload.project_name)

    ProjectRepository(db).get_or_create_by_name(payload.project_name)
    db.commit()

    span_repo = SpanRepository()
    trace_repo = TraceRepository()
    span_service = SpanService(span_repo)
    service = TraceService(trace_repo)
    try:
        trace = await service.ingest_trace(payload, span_service=span_service)
        flagged, reasons = evaluate_governance(payload.prompt, db=db)
        if flagged:
            trace.flagged_for_governance = True
            await trace.save()
        await publish_trace_update_event(trace, trace_repo)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist trace: {exc}",
        ) from exc

    return IngestResponse(request_id=payload.request_id)


@router.get("/metrics", response_model=MetricsResponse, status_code=status.HTTP_200_OK)
async def get_metrics(
    project_name: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("viewer", "analyst", "ingest")),
) -> MetricsResponse:
    scoped_projects = resolve_project_scopes(principal, project_name)
    service = TraceService(TraceRepository())
    return await service.get_metrics(
        window_size=settings.metrics_window_size,
        project_names=scoped_projects,
    )
