from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.session import get_db
from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import (
    PolicyCreateRequest,
    PolicyEvaluateResponse,
    PolicyExceptionCreateRequest,
    PolicyExceptionResponse,
    PolicyResponse,
    PolicyTestRequest,
    PolicyTestResult,
    PolicyUpdateRequest,
)
from app.services.policy_service import PolicyService

router = APIRouter(prefix="")


@router.get("/policies", response_model=list[PolicyResponse])
def list_policies(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[PolicyResponse]:
    repo = PolicyRepository(db)
    return [PolicyService._to_response(p) for p in repo.list_all()]


@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreateRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> PolicyResponse:
    repo = PolicyRepository(db)
    policy = repo.create(payload)
    return PolicyService._to_response(policy)


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> PolicyResponse:
    repo = PolicyRepository(db)
    policy = repo.get_by_id(policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return PolicyService._to_response(policy)


@router.put("/policies/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: int,
    payload: PolicyUpdateRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> PolicyResponse:
    repo = PolicyRepository(db)
    policy = repo.update(policy_id, payload)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return PolicyService._to_response(policy)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> None:
    repo = PolicyRepository(db)
    if not repo.delete(policy_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")


@router.post("/policies/test", response_model=list[PolicyTestResult])
def test_policies(
    payload: PolicyTestRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[PolicyTestResult]:
    repo = PolicyRepository(db)
    service = PolicyService(repo)
    _, reasons = service.evaluate_prompt(payload.prompt)
    return [
        PolicyTestResult(
            policy_id=r["policy_id"],
            policy_name=r["policy_name"],
            matched=r["matched"],
            reason=r.get("reason"),
        )
        for r in reasons
    ]


@router.post("/policies/{policy_id}/test", response_model=PolicyTestResult)
def test_single_policy(
    policy_id: int,
    payload: PolicyTestRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> PolicyTestResult:
    repo = PolicyRepository(db)
    service = PolicyService(repo)
    return service.evaluate_prompt_for_policy(policy_id, payload.prompt)


@router.post("/policies/{policy_id}/evaluate", response_model=PolicyEvaluateResponse)
def evaluate_policy(
    policy_id: int,
    payload: PolicyTestRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("analyst", "ingest")),
) -> PolicyEvaluateResponse:
    repo = PolicyRepository(db)
    service = PolicyService(repo)
    result = service.evaluate_prompt_for_policy(policy_id, payload.prompt)
    if result.matched:
        return PolicyEvaluateResponse(
            decision=result.action,
            matched_policies=[result],
        )
    return PolicyEvaluateResponse(decision="allow", matched_policies=[])


@router.post("/policies/evaluate", response_model=PolicyEvaluateResponse)
def evaluate_all_policies(
    payload: PolicyTestRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("analyst", "ingest")),
) -> PolicyEvaluateResponse:
    repo = PolicyRepository(db)
    service = PolicyService(repo)
    flagged, reasons = service.evaluate_prompt(payload.prompt)
    if not flagged:
        return PolicyEvaluateResponse(decision="allow", matched_policies=[])
    actions = {r["action"] for r in reasons}
    if "block" in actions:
        decision = "block"
    elif "require_approval" in actions:
        decision = "require_approval"
    else:
        decision = "flag"
    return PolicyEvaluateResponse(
        decision=decision,
        matched_policies=[
            PolicyTestResult(
                policy_id=r["policy_id"],
                policy_name=r["policy_name"],
                matched=r["matched"],
                reason=r.get("reason"),
                action=r.get("action", "flag"),
            )
            for r in reasons
        ],
    )


# Policy Exceptions
@router.get("/policies/{policy_id}/exceptions", response_model=list[PolicyExceptionResponse])
def list_exceptions(
    policy_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> list[PolicyExceptionResponse]:
    repo = PolicyRepository(db)
    exceptions = repo.list_exceptions(policy_id)
    return [
        PolicyExceptionResponse(
            id=e.id, policy_id=e.policy_id, pattern=e.pattern, reason=e.reason, created_at=e.created_at
        )
        for e in exceptions
    ]


@router.post(
    "/policies/{policy_id}/exceptions",
    response_model=PolicyExceptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_exception(
    policy_id: int,
    payload: PolicyExceptionCreateRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> PolicyExceptionResponse:
    repo = PolicyRepository(db)
    policy = repo.get_by_id(policy_id)
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    payload.policy_id = policy_id
    exc = repo.create_exception(payload)
    return PolicyExceptionResponse(
        id=exc.id, policy_id=exc.policy_id, pattern=exc.pattern, reason=exc.reason, created_at=exc.created_at
    )


@router.delete("/exceptions/{exception_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_exception(
    exception_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> None:
    repo = PolicyRepository(db)
    if not repo.delete_exception(exception_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")
