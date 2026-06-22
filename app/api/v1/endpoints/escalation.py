from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.session import get_db
from app.repositories.escalation_rule_repository import EscalationRuleRepository
from app.schemas.escalation import (
    EscalationRuleCreate,
    EscalationRuleResponse,
    EscalationRuleUpdate,
)

router = APIRouter(prefix="")


@router.get("/escalation-rules", response_model=list[EscalationRuleResponse])
def list_escalation_rules(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[EscalationRuleResponse]:
    repo = EscalationRuleRepository(db)
    return [EscalationRuleResponse.model_validate(r) for r in repo.list_all()]


@router.post("/escalation-rules", response_model=EscalationRuleResponse, status_code=status.HTTP_201_CREATED)
def create_escalation_rule(
    payload: EscalationRuleCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> EscalationRuleResponse:
    repo = EscalationRuleRepository(db)
    return EscalationRuleResponse.model_validate(repo.create(payload))


@router.get("/escalation-rules/{rule_id}", response_model=EscalationRuleResponse)
def get_escalation_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> EscalationRuleResponse:
    repo = EscalationRuleRepository(db)
    rule = repo.get_by_id(rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation rule not found")
    return EscalationRuleResponse.model_validate(rule)


@router.put("/escalation-rules/{rule_id}", response_model=EscalationRuleResponse)
def update_escalation_rule(
    rule_id: int,
    payload: EscalationRuleUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> EscalationRuleResponse:
    repo = EscalationRuleRepository(db)
    rule = repo.update(rule_id, payload)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation rule not found")
    return EscalationRuleResponse.model_validate(rule)


@router.delete("/escalation-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_escalation_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> None:
    repo = EscalationRuleRepository(db)
    if not repo.delete(rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation rule not found")


@router.get("/reviews/escalated", response_model=list[dict])
async def list_escalated_reviews(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[dict]:
    from app.repositories.audit_log_repository import AuditLogRepository
    from app.repositories.review_repository import ReviewRepository
    from app.repositories.trace_repository import TraceRepository
    from app.services.oversight_service import OversightService

    trace_repo = TraceRepository()
    review_repo = ReviewRepository(db)
    audit_repo = AuditLogRepository(db)
    service = OversightService(trace_repo, review_repo, audit_repo)

    pending = await service.get_pending_reviews()
    return [p.model_dump(mode="json") for p in pending]
