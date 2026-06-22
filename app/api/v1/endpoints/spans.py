from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.session import get_db
from app.repositories.span_repository import SpanRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.span import SpanCreateRequest, SpanResponse, SpanTreeResponse, SpanUpdateRequest
from app.services.span_service import SpanService

router = APIRouter(prefix="")


@router.post("/traces/{trace_request_id}/spans", response_model=SpanResponse, status_code=status.HTTP_201_CREATED)
async def create_span(
    trace_request_id: str,
    payload: SpanCreateRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("analyst", "ingest")),
) -> SpanResponse:
    service = SpanService(SpanRepository())
    return await service.create_span(payload)


@router.patch("/spans/{span_id}", response_model=SpanResponse)
async def update_span(
    span_id: str,
    payload: SpanUpdateRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("analyst", "ingest")),
) -> SpanResponse:
    service = SpanService(SpanRepository())
    result = await service.update_span(span_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Span not found")
    return result


@router.get("/traces/{trace_request_id}/spans", response_model=list[SpanResponse])
async def list_spans(
    trace_request_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("viewer", "analyst")),
) -> list[SpanResponse]:
    trace_repo = TraceRepository()
    trace = await trace_repo.get_by_request_id(trace_request_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    service = SpanService(SpanRepository())
    return await service.get_spans_for_trace(trace_request_id)


@router.get("/traces/{trace_request_id}/spans/tree", response_model=list[SpanTreeResponse])
async def get_span_tree(
    trace_request_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("viewer", "analyst")),
) -> list[SpanTreeResponse]:
    trace_repo = TraceRepository()
    trace = await trace_repo.get_by_request_id(trace_request_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    service = SpanService(SpanRepository())
    return await service.get_span_tree(trace_request_id)
