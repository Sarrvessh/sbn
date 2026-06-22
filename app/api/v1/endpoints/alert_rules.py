from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.session import get_db
from app.repositories.alert_rule_repository import AlertRuleRepository
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleResponse, AlertRuleUpdate

router = APIRouter(prefix="")


@router.get("/alert-rules", response_model=list[AlertRuleResponse])
def list_alert_rules(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[AlertRuleResponse]:
    repo = AlertRuleRepository(db)
    return [AlertRuleResponse.model_validate(r) for r in repo.list_all()]


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    payload: AlertRuleCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> AlertRuleResponse:
    repo = AlertRuleRepository(db)
    return AlertRuleResponse.model_validate(repo.create(payload))


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(
    rule_id: int,
    payload: AlertRuleUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> AlertRuleResponse:
    repo = AlertRuleRepository(db)
    rule = repo.update(rule_id, payload)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return AlertRuleResponse.model_validate(rule)


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> None:
    repo = AlertRuleRepository(db)
    if not repo.delete(rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
