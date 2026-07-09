from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.session import get_db
from app.repositories.webhook_repository import WebhookRepository
from app.schemas.webhook import (
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookTestRequest,
    WebhookTestResponse,
    WebhookUpdate,
)
from app.services.webhook_service import test_webhook_delivery as _test_webhook_svc

router = APIRouter(prefix="")


@router.get("/webhooks", response_model=list[WebhookResponse])
def list_webhooks(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[WebhookResponse]:
    repo = WebhookRepository(db)
    return [WebhookResponse.model_validate(w) for w in repo.list_all()]


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> WebhookResponse:
    repo = WebhookRepository(db)
    return WebhookResponse.model_validate(repo.create(payload))


@router.put("/webhooks/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: int,
    payload: WebhookUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> WebhookResponse:
    repo = WebhookRepository(db)
    hook = repo.update(webhook_id, payload)
    if hook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return WebhookResponse.model_validate(hook)


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> None:
    repo = WebhookRepository(db)
    if not repo.delete(webhook_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")


@router.get("/webhooks/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
def list_deliveries(
    webhook_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin", "analyst")),
) -> list[WebhookDeliveryResponse]:
    repo = WebhookRepository(db)
    if repo.get_by_id(webhook_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return [WebhookDeliveryResponse.model_validate(d) for d in repo.list_deliveries(webhook_id, limit=limit)]


@router.post("/webhooks/test", response_model=WebhookTestResponse)
async def test_webhook_endpoint(
    payload: WebhookTestRequest,
    _: Principal = Depends(require_roles("admin")),
) -> WebhookTestResponse:
    result = await _test_webhook_svc(payload.url, payload.secret)
    return WebhookTestResponse(**result)
