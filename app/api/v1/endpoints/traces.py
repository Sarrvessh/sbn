from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles, resolve_project_scopes
from app.db.session import get_db
from app.repositories.trace_repository import TraceRepository
from app.schemas.span import SpanResponse
from app.schemas.trace import TraceDetailResponse
from app.services.pii_redaction_service import redact_text

router = APIRouter(prefix="")


@router.get("/traces/{request_id}", response_model=TraceDetailResponse, status_code=status.HTTP_200_OK)
async def get_trace_detail(
    request_id: str,
    redact: bool = Query(default=False),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("viewer", "analyst")),
) -> TraceDetailResponse:
    repository = TraceRepository()
    trace = await repository.get_by_request_id(request_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    resolve_project_scopes(principal, trace.project_name)

    prompt = redact_text(trace.prompt) if redact else trace.prompt
    response_text = redact_text(trace.response) if redact else trace.response

    return TraceDetailResponse(
        request_id=trace.request_id,
        project_name=trace.project_name,
        prompt=prompt,
        response=response_text,
        model_name=trace.model_name,
        total_tokens=trace.total_tokens,
        cost=trace.cost,
        latency_ms=trace.latency_ms,
        status=trace.status,
        flagged_for_governance=trace.flagged_for_governance,
        timestamp=trace.timestamp,
        spans=[SpanResponse(**s.model_dump(exclude={"project_name"})) for s in trace.spans],
    )


@router.post("/traces/{request_id}/flag", response_model=TraceDetailResponse)
async def flag_trace(
    request_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin", "analyst")),
) -> TraceDetailResponse:
    repository = TraceRepository()
    trace = await repository.get_by_request_id(request_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    resolve_project_scopes(principal, trace.project_name)
    trace.flagged_for_governance = True
    await trace.save()
    return TraceDetailResponse(
        request_id=trace.request_id,
        project_name=trace.project_name,
        prompt=trace.prompt,
        response=trace.response,
        model_name=trace.model_name,
        total_tokens=trace.total_tokens,
        cost=trace.cost,
        latency_ms=trace.latency_ms,
        status=trace.status,
        flagged_for_governance=trace.flagged_for_governance,
        timestamp=trace.timestamp,
        spans=[SpanResponse(**s.model_dump(exclude={"project_name"})) for s in trace.spans],
    )


@router.post("/traces/{request_id}/unflag", response_model=TraceDetailResponse)
async def unflag_trace(
    request_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin", "analyst")),
) -> TraceDetailResponse:
    repository = TraceRepository()
    trace = await repository.get_by_request_id(request_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    resolve_project_scopes(principal, trace.project_name)
    trace.flagged_for_governance = False
    await trace.save()
    return TraceDetailResponse(
        request_id=trace.request_id,
        project_name=trace.project_name,
        prompt=trace.prompt,
        response=trace.response,
        model_name=trace.model_name,
        total_tokens=trace.total_tokens,
        cost=trace.cost,
        latency_ms=trace.latency_ms,
        status=trace.status,
        flagged_for_governance=trace.flagged_for_governance,
        timestamp=trace.timestamp,
        spans=[SpanResponse(**s.model_dump(exclude={"project_name"})) for s in trace.spans],
    )



