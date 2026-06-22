from __future__ import annotations

from app.db.mongo_models import TraceDocument
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.trace_repository import TraceRepository
from app.schemas.oversight import PendingReviewItem, ReviewCreate, ReviewResponse


class OversightService:
    def __init__(
        self, trace_repo: TraceRepository, review_repo: ReviewRepository,
        audit_repo: AuditLogRepository,
    ) -> None:
        self._trace_repo = trace_repo
        self._review_repo = review_repo
        self._audit_repo = audit_repo

    async def get_pending_reviews(self) -> list[PendingReviewItem]:
        traces = await self._trace_repo.list_flagged(limit=500)
        result: list[PendingReviewItem] = []

        for t in traces:
            latest = self._review_repo.get_latest_for_request(t.request_id)
            if latest and latest.decision in ("approved", "rejected"):
                continue
            result.append(self._to_pending_item(t, latest))

        return result

    async def get_reviewed_traces(self) -> list[PendingReviewItem]:
        traces = await self._trace_repo.list_flagged(limit=500)
        result: list[PendingReviewItem] = []

        for t in traces:
            latest = self._review_repo.get_latest_for_request(t.request_id)
            if latest and latest.decision in ("approved", "rejected"):
                result.append(self._to_pending_item(t, latest))

        return result

    async def create_review(self, payload: ReviewCreate) -> ReviewResponse:
        review = self._review_repo.create(payload)
        self._audit_repo.record(
            actor=payload.reviewer,
            action="review_create",
            resource_type="trace",
            resource_id=payload.request_id,
            details={"decision": payload.decision, "notes": payload.notes},
        )
        return ReviewResponse(
            id=review.id,
            request_id=review.request_id,
            reviewer=review.reviewer,
            decision=review.decision,
            notes=review.notes,
            created_at=review.created_at,
        )

    def get_reviews_for_trace(self, request_id: str) -> list[ReviewResponse]:
        reviews = self._review_repo.get_by_request_id(request_id)
        return [
            ReviewResponse(
                id=r.id,
                request_id=r.request_id,
                reviewer=r.reviewer,
                decision=r.decision,
                notes=r.notes,
                created_at=r.created_at,
            )
            for r in reviews
        ]

    def record_audit(
        self, actor: str, action: str, resource_type: str,
        resource_id: str | None = None, details: dict | None = None,
    ):
        return self._audit_repo.record(actor, action, resource_type, resource_id, details)

    def get_audit_log(
        self, limit: int = 100, offset: int = 0,
        actor: str | None = None, action: str | None = None,
        resource_type: str | None = None,
    ):
        return self._audit_repo.list_all(limit, offset, actor, action, resource_type)

    def _to_pending_item(self, trace: TraceDocument, latest_review) -> PendingReviewItem:
        return PendingReviewItem(
            request_id=trace.request_id,
            project_name=trace.project_name,
            model_name=trace.model_name,
            total_tokens=trace.total_tokens,
            cost=trace.cost,
            prompt_preview=(trace.prompt or "")[:200],
            response_preview=(trace.response or "")[:200],
            timestamp=trace.timestamp,
            latest_review=latest_review,
        )
