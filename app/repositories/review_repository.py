from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Review
from app.schemas.oversight import ReviewCreate


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, payload: ReviewCreate) -> Review:
        review = Review(
            request_id=payload.request_id,
            reviewer=payload.reviewer,
            decision=payload.decision,
            notes=payload.notes,
        )
        self._db.add(review)
        self._db.commit()
        self._db.refresh(review)
        return review

    def get_by_request_id(self, request_id: str) -> list[Review]:
        stmt = (
            select(Review)
            .where(Review.request_id == request_id)
            .order_by(desc(Review.created_at))
        )
        return list(self._db.scalars(stmt).all())

    def get_latest_for_request(self, request_id: str) -> Review | None:
        stmt = (
            select(Review)
            .where(Review.request_id == request_id)
            .order_by(desc(Review.created_at))
            .limit(1)
        )
        return self._db.scalar(stmt)

    def list_pending_request_ids(self) -> list[str]:
        subq = (
            select(
                Review.request_id,
            )
            .where(Review.decision.in_(["approved", "rejected"]))
            .distinct()
            .subquery()
        )
        stmt = (
            select(Review.request_id)
            .where(Review.request_id.notin_(select(subq.c.request_id)))
            .distinct()
        )
        reviewed = set(self._db.scalars(stmt).all())

        stmt_all = select(Review.request_id).distinct()
        all_with_reviews = set(self._db.scalars(stmt_all).all())

        pending = all_with_reviews - reviewed
        return list(pending)
