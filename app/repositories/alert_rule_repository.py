from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AlertRule
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleUpdate


class AlertRuleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[AlertRule]:
        return list(self._db.scalars(select(AlertRule).order_by(AlertRule.name)).all())

    def get_by_id(self, rule_id: int) -> AlertRule | None:
        return self._db.get(AlertRule, rule_id)

    def create(self, payload: AlertRuleCreate) -> AlertRule:
        rule = AlertRule(
            name=payload.name,
            project_name=payload.project_name,
            alert_type=payload.alert_type,
            severity=payload.severity,
            threshold_value=payload.threshold_value,
            enabled=payload.enabled,
        )
        self._db.add(rule)
        self._db.commit()
        self._db.refresh(rule)
        return rule

    def update(self, rule_id: int, payload: AlertRuleUpdate) -> AlertRule | None:
        rule = self.get_by_id(rule_id)
        if rule is None:
            return None
        if payload.name is not None:
            rule.name = payload.name
        if payload.project_name is not None:
            rule.project_name = payload.project_name
        if payload.alert_type is not None:
            rule.alert_type = payload.alert_type
        if payload.severity is not None:
            rule.severity = payload.severity
        if payload.threshold_value is not None:
            rule.threshold_value = payload.threshold_value
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

    def get_matching(self, project_name: str, alert_type: str) -> list[AlertRule]:
        stmt = (
            select(AlertRule)
            .where(
                AlertRule.enabled.is_(True),
                AlertRule.alert_type == alert_type,
            )
            .where(
                (AlertRule.project_name == project_name) | (AlertRule.project_name.is_(None)),
            )
            .order_by(AlertRule.project_name.is_(None).asc(), AlertRule.id.asc())
        )
        return list(self._db.scalars(stmt).all())
