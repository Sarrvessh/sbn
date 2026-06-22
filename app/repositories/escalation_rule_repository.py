from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EscalationRule
from app.schemas.escalation import EscalationRuleCreate, EscalationRuleUpdate


class EscalationRuleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[EscalationRule]:
        return list(self._db.scalars(select(EscalationRule).order_by(EscalationRule.name)).all())

    def get_by_id(self, rule_id: int) -> EscalationRule | None:
        return self._db.get(EscalationRule, rule_id)

    def create(self, payload: EscalationRuleCreate) -> EscalationRule:
        rule = EscalationRule(
            name=payload.name,
            description=payload.description,
            rule_type=payload.rule_type,
            rule_config=payload.rule_config,
            target_role=payload.target_role,
        )
        self._db.add(rule)
        self._db.commit()
        self._db.refresh(rule)
        return rule

    def update(self, rule_id: int, payload: EscalationRuleUpdate) -> EscalationRule | None:
        rule = self.get_by_id(rule_id)
        if rule is None:
            return None
        if payload.name is not None:
            rule.name = payload.name
        if payload.description is not None:
            rule.description = payload.description
        if payload.rule_type is not None:
            rule.rule_type = payload.rule_type
        if payload.rule_config is not None:
            rule.rule_config = payload.rule_config
        if payload.target_role is not None:
            rule.target_role = payload.target_role
        if payload.enabled is not None:
            rule.enabled = payload.enabled
        self._db.commit()
        self._db.refresh(rule)
        return rule

    def delete(self, rule_id: int) -> bool:
        rule = self.get_by_id(rule_id)
        if rule is None:
            return False
        self._db.delete(rule)
        self._db.commit()
        return True

    def find_matching(self, severity: str) -> list[EscalationRule]:
        stmt = select(EscalationRule).where(
            EscalationRule.enabled.is_(True),
            EscalationRule.rule_config["severity"].as_string() == severity,
        )
        return list(self._db.scalars(stmt).all())
