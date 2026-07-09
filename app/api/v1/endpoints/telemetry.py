"""HTTP endpoints for telemetry ingest and metrics retrieval — async with MongoDB."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="")


async def _post_ingest_task(
    request_id: str, prompt: str, db: Session,
) -> None:
    """Background task: evaluate governance and publish realtime event."""
    trace_repo = TraceRepository()
    try:
        trace = await trace_repo.get_by_request_id(request_id)
        if trace is None:
            return
        flagged, _ = evaluate_governance(prompt, db=db)
        if flagged:
            trace.flagged_for_governance = True
            await trace.save()
        await publish_trace_update_event(trace, trace_repo)
    except Exception:
        logger.exception("Post-ingest processing failed for %s", request_id)


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_trace(
    payload: TraceIngestRequest,
    background_tasks: BackgroundTasks,
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
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist trace: {exc}",
        ) from exc

    background_tasks.add_task(_post_ingest_task, trace.request_id, payload.prompt, db)
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
