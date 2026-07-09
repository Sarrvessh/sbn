"""Endpoints for live agent execution and realtime analytics — async."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    Principal,
    require_roles,
    resolve_project_scope,
    resolve_project_scopes,
)
from app.db.session import get_db
from app.repositories.span_repository import SpanRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.schemas.analytics import (
    AlertResponse,
    GovernanceMetricsResponse,
    RealtimeMetricsResponse,
    RecentTraceResponse,
    SystemMetricsResponse,
)
from app.schemas.trace import TraceIngestRequest
from app.services.event_stream_service import event_stream_service
from app.services.governance_service import evaluate_governance
from app.services.openai_agent_service import AgentExecutionError, OpenAIAgentService
from app.services.pii_redaction_service import redact_dict
from app.services.realtime_analyzer_service import RealtimeAnalyzerService
from app.services.realtime_event_publisher import publish_trace_update_event
from app.services.span_service import SpanService
from app.services.trace_service import TraceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="")


async def _agent_post_ingest_task(
    request_id: str, db: Session,
) -> None:
    """Background task: publish realtime event after agent execution."""
    trace_repo = TraceRepository()
    try:
        trace = await trace_repo.get_by_request_id(request_id)
        if trace is None:
            return
        await publish_trace_update_event(trace, trace_repo, db=db)
    except Exception:
        logger.exception("Post-agent event publish failed for %s", request_id)


@router.post("/agent/run", response_model=AgentRunResponse, status_code=status.HTTP_200_OK)
async def run_agent(
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("analyst")),
) -> AgentRunResponse:
    effective_project_name = resolve_project_scope(principal, request.project_name)
    if effective_project_name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_name is required")

    request_id = uuid4().hex
    started_at = perf_counter()
    timestamp = datetime.now(timezone.utc)
    flagged, reasons = evaluate_governance(request.prompt, db)

    span_service = SpanService(SpanRepository())
    service = TraceService(TraceRepository())

    try:
        agent = OpenAIAgentService()
        agent_result = agent.run_prompt(
            prompt=request.prompt, model_name=request.model_name,
            max_tokens=request.max_tokens, temperature=request.temperature,
        )
        latency_ms = (perf_counter() - started_at) * 1000

        payload = TraceIngestRequest(
            request_id=request_id, project_name=effective_project_name,
            prompt=request.prompt, response=agent_result.response_text,
            model_name=request.model_name, total_tokens=agent_result.total_tokens,
            cost=agent_result.cost, latency_ms=max(latency_ms, 0.001),
            status="success", flagged_for_governance=flagged, timestamp=timestamp,
        )
        trace = await service.ingest_trace(payload, span_service=span_service)
        background_tasks.add_task(_agent_post_ingest_task, trace.request_id, db)

        return AgentRunResponse(
            request_id=request_id, project_name=effective_project_name,
            status="success", model_name=request.model_name,
            response=agent_result.response_text, total_tokens=agent_result.total_tokens,
            cost=agent_result.cost, latency_ms=max(latency_ms, 0.001),
            flagged_for_governance=flagged, governance_reasons=reasons, timestamp=timestamp,
        )
    except AgentExecutionError as exc:
        latency_ms = (perf_counter() - started_at) * 1000
        error_message = str(exc)
        try:
            payload = TraceIngestRequest(
                request_id=request_id, project_name=effective_project_name,
                prompt=request.prompt, response=error_message,
                model_name=request.model_name, total_tokens=0, cost=0.0,
                latency_ms=max(latency_ms, 0.001), status="error",
                flagged_for_governance=flagged, timestamp=timestamp,
            )
            trace = await service.ingest_trace(payload, span_service=span_service)
            background_tasks.add_task(_agent_post_ingest_task, trace.request_id, db)
        except Exception as exc2:
            logger.warning("Failed to persist error trace: %s", exc2)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error_message) from exc


@router.get("/analytics/realtime", response_model=RealtimeMetricsResponse, status_code=status.HTTP_200_OK)
async def get_realtime_metrics(
    project_name: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("viewer", "analyst")),
) -> RealtimeMetricsResponse:
    scoped_projects = resolve_project_scopes(principal, project_name)
    service = RealtimeAnalyzerService(TraceRepository())
    return await service.get_realtime_metrics(
        window_size=settings.metrics_window_size, project_names=scoped_projects,
    )


@router.get("/traces/recent", response_model=list[RecentTraceResponse])
async def get_recent_traces(
    limit: int = Query(default=100, ge=1, le=500),
    project_name: str | None = Query(default=None, max_length=255),
    redact: bool = Query(default=False),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("viewer", "analyst")),
) -> list[RecentTraceResponse]:
    scoped_projects = resolve_project_scopes(principal, project_name)
    service = RealtimeAnalyzerService(TraceRepository())
    traces = await service.get_recent_traces(limit=limit, project_names=scoped_projects)
    if redact:
        traces = [RecentTraceResponse(**redact_dict(t.model_dump(mode="json"))) for t in traces]
    return traces


@router.get("/alerts", response_model=list[AlertResponse])
async def get_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    project_name: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("viewer", "analyst")),
) -> list[AlertResponse]:
    scoped_projects = resolve_project_scopes(principal, project_name)
    service = RealtimeAnalyzerService(TraceRepository())
    return await service.get_alerts(limit=limit, project_names=scoped_projects, db=db)


@router.get("/analytics/governance", response_model=GovernanceMetricsResponse)
async def get_governance_metrics(
    project_name: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("viewer", "analyst")),
) -> GovernanceMetricsResponse:
    scoped_projects = resolve_project_scopes(principal, project_name)
    trace_repo = TraceRepository()

    total = await trace_repo.get_trace_count(project_names=scoped_projects)
    flagged = await trace_repo.get_governance_flagged_count(project_names=scoped_projects)
    flag_rate = round((flagged / total * 100), 2) if total > 0 else 0.0

    from sqlalchemy import func as sa_func
    from sqlalchemy import select

    from app.db.models import Review
    from app.repositories.review_repository import ReviewRepository

    review_repo = ReviewRepository(db)
    pending_ids = review_repo.list_pending_request_ids()
    approved = db.scalar(select(sa_func.count()).where(Review.decision == "approved"))
    rejected = db.scalar(select(sa_func.count()).where(Review.decision == "rejected"))

    flagged_traces = await trace_repo.list_flagged(limit=10, project_names=scoped_projects)
    recent = []
    for ft in flagged_traces[:5]:
        recent.append({
            "request_id": ft.request_id,
            "project_name": ft.project_name,
            "model_name": ft.model_name,
            "timestamp": ft.timestamp.isoformat() if ft.timestamp else None,
            "status": ft.status,
        })

    from app.repositories.policy_repository import PolicyRepository
    policy_repo = PolicyRepository(db)
    policies = policy_repo.list_all()
    by_severity: dict[str, int] = {}
    for p in policies:
        by_severity[p.severity] = by_severity.get(p.severity, 0) + 1

    return GovernanceMetricsResponse(
        total_traces=total,
        total_flagged=flagged,
        flag_rate=flag_rate,
        pending_reviews=len(pending_ids),
        approved_reviews=approved or 0,
        rejected_reviews=rejected or 0,
        by_severity=[{"severity": k, "count": v} for k, v in by_severity.items()],
        recent_flags=recent,
    )


@router.get("/analytics/system", response_model=SystemMetricsResponse)
async def get_system_metrics(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("viewer", "analyst")),
) -> SystemMetricsResponse:
    trace_repo = TraceRepository()

    total_traces = await trace_repo.get_trace_count()
    total_tokens = await trace_repo.get_total_tokens()
    total_cost = await trace_repo.get_total_cost()
    err_rate = await trace_repo.get_error_rate_last_n(200)
    avg_lat = await trace_repo.get_average_latency_last_n(200)
    traces_today = await trace_repo.get_trace_count_last_24h()

    from app.repositories.project_repository import ProjectRepository
    db_projects = ProjectRepository(db).list_all()

    from app.db.models import Trace
    models_raw = db.query(Trace.model_name).distinct().order_by(Trace.model_name).all()
    unique_models = [m[0] for m in models_raw if m[0]]

    uptime_hours = (datetime.now(timezone.utc) - settings.app_start_time).total_seconds() / 3600 if hasattr(settings, "app_start_time") else 0.0

    return SystemMetricsResponse(
        total_traces=total_traces,
        total_projects=len(db_projects),
        error_rate=err_rate,
        average_latency_ms=avg_lat,
        total_tokens=total_tokens,
        total_cost=total_cost,
        unique_models=unique_models,
        traces_today=traces_today,
        uptime_hours=round(uptime_hours, 2),
    )


@router.get("/events/stream")
async def stream_events(
    request: Request,
    project_name: str | None = Query(default=None, max_length=255),
    last_event_id: str | None = Query(default=None),
    principal: Principal = Depends(require_roles("viewer", "analyst")),
) -> StreamingResponse:
    scoped_projects = resolve_project_scopes(principal, project_name)
    subscriber_id = event_stream_service.subscribe(
        project_names=(set(scoped_projects) if scoped_projects is not None else None)
    )

    async def event_generator():
        try:
            yield _format_sse({
                "event_type": "connected",
                "project_scopes": scoped_projects,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, event_name="connected")
            while True:
                if await request.is_disconnected():
                    break
                event = await asyncio.to_thread(event_stream_service.get_next_event, subscriber_id, 15.0)
                if event is None:
                    yield _format_sse({
                        "event_type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }, event_name="heartbeat")
                    continue
                yield _format_sse(event, event_name=event.get("event_type", "message"))
        finally:
            event_stream_service.unsubscribe(subscriber_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _format_sse(payload: dict, event_name: str) -> str:
    clean = {k: v for k, v in payload.items() if k != "event_id"}
    event_id = payload.get("event_id")
    out = f"event: {event_name}\n"
    if event_id is not None:
        out += f"id: {event_id}\n"
    out += f"data: {json.dumps(clean)}\n\n"
    return out


@router.websocket("/events/ws")
async def stream_events_ws(
    websocket: WebSocket,
    project_name: str | None = Query(default=None),
    last_event_id: str | None = Query(default=None),
) -> None:
    api_key = websocket.headers.get(settings.api_key_header_name) or websocket.query_params.get("api_key")
    if not api_key:
        await websocket.close(code=4001)
        return
    from app.db.session import SessionLocal
    from app.repositories.api_key_repository import ApiKeyRepository, hash_api_key

    db = SessionLocal()
    try:
        repo = ApiKeyRepository(db)
        record = repo.get_active_by_hash(hash_api_key(api_key))
        if record is None or record.role not in ("viewer", "analyst", "admin"):
            await websocket.close(code=4003)
            return
        scoped = None
        if record.project_scope:
            normalized = record.project_scope.replace(";", ",")
            tokens = [s.strip() for s in normalized.split(",") if s.strip()]
            if tokens:
                scoped = list(dict.fromkeys(tokens))

        scoped_projects: list[str] | None = None
        if project_name and scoped:
            if project_name not in scoped:
                await websocket.close(code=4003)
                return
            scoped_projects = [project_name]
        elif scoped:
            scoped_projects = scoped
        elif project_name:
            scoped_projects = [project_name]

        subscriber_id = event_stream_service.subscribe(
            project_names=(set(scoped_projects) if scoped_projects is not None else None)
        )
    finally:
        db.close()

    await websocket.accept()
    try:
        await websocket.send_json({
            "event_type": "connected",
            "project_scopes": scoped_projects,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": 0,
        })
        while True:
            event = await asyncio.to_thread(event_stream_service.get_next_event, subscriber_id, 15.0)
            if event is None:
                try:
                    await asyncio.wait_for(
                        websocket.send_json({
                            "event_type": "heartbeat",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }),
                        timeout=5.0,
                    )
                except Exception:
                    break
                continue
            try:
                await asyncio.wait_for(
                    websocket.send_json(event),
                    timeout=5.0,
                )
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        event_stream_service.unsubscribe(subscriber_id)
