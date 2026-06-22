from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging

import httpx
from sqlalchemy.orm import Session

from app.db.models import Webhook
from app.repositories.webhook_repository import WebhookRepository

logger = logging.getLogger(__name__)
_TIMEOUT_SECONDS = 10


def _compute_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def deliver_webhook(webhook: Webhook, event_type: str, payload: dict) -> dict:
    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-SBN-Signature": _compute_signature(webhook.secret or "", body),
        "X-SBN-Event": event_type,
    }
    result = {"webhook_id": webhook.id, "event_type": event_type}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(webhook.url, content=body, headers=headers)
        result["status"] = "success" if resp.is_success else "fail"
        result["status_code"] = resp.status_code
        result["response_body"] = resp.text[:2000]
    except httpx.TimeoutException:
        result["status"] = "fail"
        result["status_code"] = None
        result["response_body"] = "Request timed out"
    except Exception as exc:
        result["status"] = "fail"
        result["status_code"] = None
        result["response_body"] = str(exc)[:2000]
    return result


async def deliver_event(event_type: str, payload: dict, db: Session) -> list[dict]:
    repo = WebhookRepository(db)
    webhooks = repo.get_enabled_by_events([event_type])
    if not webhooks:
        return []

    tasks = [deliver_webhook(w, event_type, payload) for w in webhooks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    delivery_results: list[dict] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error("Webhook delivery failed with exception: %s", result)
            continue
        repo.log_delivery(
            webhook_id=result["webhook_id"],
            event_type=result["event_type"],
            payload=payload,
            status=result["status"],
            status_code=result.get("status_code"),
            response_body=result.get("response_body"),
        )
        delivery_results.append(result)
    return delivery_results


async def test_webhook(url: str, secret: str | None) -> dict:
    test_payload = {
        "event_type": "test",
        "data": {
            "message": "This is a test webhook from SBN observability platform.",
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        },
    }
    body = json.dumps(test_payload, default=str).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-SBN-Signature"] = _compute_signature(secret, body)
    headers["X-SBN-Event"] = "test"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, content=body, headers=headers)
        return {
            "success": resp.is_success,
            "status_code": resp.status_code,
            "response_body": resp.text[:2000],
            "error": None,
        }
    except httpx.TimeoutException:
        return {"success": False, "status_code": None, "response_body": None, "error": "Request timed out"}
    except Exception as exc:
        return {"success": False, "status_code": None, "response_body": None, "error": str(exc)}
