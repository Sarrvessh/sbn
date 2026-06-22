from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Policy, PolicyException
from app.schemas.policy import PolicyCreateRequest, PolicyExceptionCreateRequest, PolicyUpdateRequest


class PolicyRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, payload: PolicyCreateRequest) -> Policy:
        policy = Policy(
            name=payload.name,
            description=payload.description,
            policy_type=payload.policy_type,
            rule_config=payload.rule_config,
            severity=payload.severity,
            enabled=payload.enabled,
            action=payload.action,
            project_scope=payload.project_scope,
        )
        self._db.add(policy)
        self._db.commit()
        self._db.refresh(policy)
        return policy

    def update(self, policy_id: int, payload: PolicyUpdateRequest) -> Policy | None:
        policy = self.get_by_id(policy_id)
        if policy is None:
            return None
        if payload.name is not None:
            policy.name = payload.name
        if payload.description is not None:
            policy.description = payload.description
        if payload.policy_type is not None:
            policy.policy_type = payload.policy_type
        if payload.rule_config is not None:
            policy.rule_config = payload.rule_config
        if payload.severity is not None:
            policy.severity = payload.severity
        if payload.enabled is not None:
            policy.enabled = payload.enabled
        if payload.project_scope is not None:
            policy.project_scope = payload.project_scope
        self._db.commit()
        self._db.refresh(policy)
        return policy

    def get_by_id(self, policy_id: int) -> Policy | None:
        return self._db.get(Policy, policy_id)

    def get_all_enabled(self) -> list[Policy]:
        statement = select(Policy).where(Policy.enabled.is_(True)).order_by(Policy.name)
        return list(self._db.scalars(statement).all())

    def list_all(self) -> list[Policy]:
        statement = select(Policy).order_by(Policy.name)
        return list(self._db.scalars(statement).all())

    def delete(self, policy_id: int) -> bool:
        policy = self.get_by_id(policy_id)
        if policy is None:
            return False
        self._db.delete(policy)
        self._db.commit()
        return True

    # Exceptions
    def create_exception(self, payload: PolicyExceptionCreateRequest) -> PolicyException:
        exc = PolicyException(
            policy_id=payload.policy_id,
            pattern=payload.pattern,
            reason=payload.reason,
        )
        self._db.add(exc)
        self._db.commit()
        self._db.refresh(exc)
        return exc

    def list_exceptions(self, policy_id: int | None = None) -> list[PolicyException]:
        statement = select(PolicyException)
        if policy_id is not None:
            statement = statement.where(PolicyException.policy_id == policy_id)
        statement = statement.order_by(PolicyException.created_at.desc())
        return list(self._db.scalars(statement).all())

    def delete_exception(self, exception_id: int) -> bool:
        exc = self._db.get(PolicyException, exception_id)
        if exc is None:
            return False
        self._db.delete(exc)
        self._db.commit()
        return True

    def is_exception(self, policy_id: int, text: str) -> bool:
        exceptions = self.list_exceptions(policy_id)
        for exc in exceptions:
            if exc.pattern.lower() in text.lower():
                return True
        return False
