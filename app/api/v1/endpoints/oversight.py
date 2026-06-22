from __future__ import annotations

import csv
import io
import json
from typing import Literal

import bson
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.mongo_models import TraceDocument
from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.oversight import (
    AuditLogResponse,
    PendingReviewItem,
    ReviewCreate,
    ReviewResponse,
)
from app.services.oversight_service import OversightService
from app.services.pii_redaction_service import redact_dict, redact_text

router = APIRouter(prefix="")


# Review Queue
@router.get("/reviews/pending", response_model=list[PendingReviewItem])
async def list_pending_reviews(
    redact: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[PendingReviewItem]:
    service = OversightService(TraceRepository(), ReviewRepository(db), AuditLogRepository(db))
    items = await service.get_pending_reviews()
    if redact:
        items = [PendingReviewItem(**redact_dict(i.model_dump(mode="json"))) for i in items]
    return items


@router.get("/reviews/reviewed", response_model=list[PendingReviewItem])
async def list_reviewed_traces(
    redact: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[PendingReviewItem]:
    service = OversightService(TraceRepository(), ReviewRepository(db), AuditLogRepository(db))
    items = await service.get_reviewed_traces()
    if redact:
        items = [PendingReviewItem(**redact_dict(i.model_dump(mode="json"))) for i in items]
    return items


@router.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles("admin", "analyst")),
) -> ReviewResponse:
    trace_repo = TraceRepository()
    trace = await trace_repo.get_by_request_id(payload.request_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    service = OversightService(TraceRepository(), ReviewRepository(db), AuditLogRepository(db))
    return await service.create_review(payload)


@router.get("/traces/{request_id}/reviews", response_model=list[ReviewResponse])
def get_trace_reviews(
    request_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("viewer", "analyst", "admin")),
) -> list[ReviewResponse]:
    service = OversightService(TraceRepository(), ReviewRepository(db), AuditLogRepository(db))
    return service.get_reviews_for_trace(request_id)


@router.get("/audit-log", response_model=list[AuditLogResponse])
def list_audit_log(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    actor: str | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> list[AuditLogResponse]:
    service = OversightService(TraceRepository(), ReviewRepository(db), AuditLogRepository(db))
    return service.get_audit_log(
        limit=limit, offset=offset, actor=actor, action=action, resource_type=resource_type,
    )


@router.get("/export/traces/batch")
async def export_traces_batch(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    redact: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> dict:
    query = {}
    if cursor:
        try:
            query["_id"] = {"$gt": bson.ObjectId(cursor)}
        except InvalidId:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor format")
    cursor_q = TraceDocument.find(query).sort("_id").limit(limit)
    traces = await cursor_q.to_list()
    data = [
        {
            "request_id": t.request_id, "project_name": t.project_name,
            "model_name": t.model_name, "prompt": t.prompt, "response": t.response,
            "total_tokens": t.total_tokens, "cost": t.cost, "latency_ms": t.latency_ms,
            "status": t.status, "flagged_for_governance": t.flagged_for_governance,
            "timestamp": t.timestamp.isoformat(),
        }
        for t in traces
    ]
    if redact:
        data = [redact_dict(d) for d in data]
    next_cursor = traces[-1].id if traces else None
    return {
        "data": data,
        "next_cursor": str(next_cursor) if next_cursor else None,
        "has_more": len(traces) == limit,
    }


@router.get("/export/traces")
async def export_traces(
    format: Literal["csv", "json"] = Query(default="json"),
    project_name: str | None = Query(default=None, max_length=255),
    redact: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> Response:
    repo = TraceRepository()
    traces = await repo.list_recent(project_names=[project_name] if project_name else None)

    if format == "json":
        data = [
            {
                "request_id": t.request_id, "project_name": t.project_name,
                "model_name": t.model_name, "prompt": t.prompt, "response": t.response,
                "total_tokens": t.total_tokens, "cost": t.cost, "latency_ms": t.latency_ms,
                "status": t.status, "flagged_for_governance": t.flagged_for_governance,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in traces
        ]
        if redact:
            data = [redact_dict(d) for d in data]
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=traces.json"},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "request_id", "project_name", "model_name", "prompt", "response",
        "total_tokens", "cost", "latency_ms", "status", "flagged_for_governance", "timestamp",
    ])
    for t in traces:
        prompt = redact_text(t.prompt) if redact else t.prompt
        response_text = redact_text(t.response) if redact else t.response
        writer.writerow([
            t.request_id, t.project_name, t.model_name, prompt, response_text,
            t.total_tokens, t.cost, t.latency_ms, t.status,
            int(t.flagged_for_governance), t.timestamp.isoformat(),
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=traces.csv"},
    )
