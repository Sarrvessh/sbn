from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def record(
        self,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        self._db.add(entry)
        self._db.commit()
        self._db.refresh(entry)
        return entry

    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        actor: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> list[AuditLog]:
        stmt = select(AuditLog)
        if actor:
            stmt = stmt.where(AuditLog.actor == actor)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        stmt = stmt.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
        return list(self._db.scalars(stmt).all())

    def count(
        self,
        actor: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> int:
        stmt = select(AuditLog)
        if actor:
            stmt = stmt.where(AuditLog.actor == actor)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        return self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
