from __future__ import annotations

from base64 import b64encode
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Webhook, WebhookDelivery
from app.schemas.webhook import WebhookCreate, WebhookUpdate


def _get_fernet() -> Fernet:
    key_material = settings.encryption_key or (settings.app_name + settings.database_url)
    key = b64encode(key_material.encode("utf-8").ljust(32, b"x")[:32])
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return token


class WebhookRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, payload: WebhookCreate) -> Webhook:
        secret_enc = encrypt_secret(payload.secret) if payload.secret else None
        hook = Webhook(
            name=payload.name,
            url=payload.url,
            secret=secret_enc,
            events=payload.events,
            enabled=payload.enabled,
        )
        self._db.add(hook)
        self._db.commit()
        self._db.refresh(hook)
        hook.secret = decrypt_secret(hook.secret) if hook.secret else None
        return hook

    def update(self, webhook_id: int, payload: WebhookUpdate) -> Webhook | None:
        hook = self.get_by_id(webhook_id)
        if hook is None:
            return None
        if payload.name is not None:
            hook.name = payload.name
        if payload.url is not None:
            hook.url = payload.url
        if payload.secret is not None:
            hook.secret = encrypt_secret(payload.secret)
        if payload.events is not None:
            hook.events = payload.events
        if payload.enabled is not None:
            hook.enabled = payload.enabled
        self._db.commit()
        self._db.refresh(hook)
        hook.secret = decrypt_secret(hook.secret) if hook.secret else None
        return hook

    def get_by_id(self, webhook_id: int) -> Webhook | None:
        hook = self._db.get(Webhook, webhook_id)
        if hook is not None and hook.secret:
            hook.secret = decrypt_secret(hook.secret)
        return hook

    def get_enabled_by_events(self, event_types: list[str]) -> list[Webhook]:
        stmt = select(Webhook).where(
            Webhook.enabled.is_(True),
            Webhook.events.contains(event_types),
        )
        hooks = list(self._db.scalars(stmt).all())
        for h in hooks:
            if h.secret:
                h.secret = decrypt_secret(h.secret)
        return hooks

    def list_all(self) -> list[Webhook]:
        stmt = select(Webhook).order_by(Webhook.name)
        hooks = list(self._db.scalars(stmt).all())
        for h in hooks:
            if h.secret:
                h.secret = decrypt_secret(h.secret)
        return hooks

    def delete(self, webhook_id: int) -> bool:
        hook = self._db.get(Webhook, webhook_id)
        if hook is None:
            return False
        self._db.delete(hook)
        self._db.commit()
        return True

    # Delivery logging
    def log_delivery(
        self,
        webhook_id: int,
        event_type: str,
        payload: dict,
        status: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> WebhookDelivery:
        delivery = WebhookDelivery(
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            status=status,
            status_code=status_code,
            response_body=response_body,
            delivered_at=datetime.now(timezone.utc),
        )
        self._db.add(delivery)
        self._db.commit()
        self._db.refresh(delivery)
        return delivery

    def list_deliveries(self, webhook_id: int, limit: int = 50) -> list[WebhookDelivery]:
        stmt = (
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == webhook_id)
            .order_by(WebhookDelivery.delivered_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt).all())
