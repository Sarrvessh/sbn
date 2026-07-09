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
_MAX_RETRIES = 3
_RETRY_DELAYS = [1, 4, 16]


def _compute_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _is_retryable(result: dict) -> bool:
    if result["status_code"] is None:
        return True
    return 500 <= result["status_code"] < 600


async def deliver_webhook(webhook: Webhook, event_type: str, payload: dict) -> dict:
    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-SBN-Signature": _compute_signature(webhook.secret or "", body),
        "X-SBN-Event": event_type,
    }
    last_result: dict | None = None
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            result: dict = {"webhook_id": webhook.id, "event_type": event_type}
            try:
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

            if result["status"] == "success":
                return result

            last_result = result
            if attempt < _MAX_RETRIES and _is_retryable(result):
                wait = _RETRY_DELAYS[attempt - 1]
                logger.warning(
                    "Webhook %d delivery attempt %d failed, retrying in %ds: %s",
                    webhook.id, attempt, wait, result.get("response_body", ""),
                )
                await asyncio.sleep(wait)
            else:
                break

    logger.error("Webhook %d delivery failed after %d attempts", webhook.id, _MAX_RETRIES)
    return last_result or {"webhook_id": webhook.id, "event_type": event_type, "status": "fail"}


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


async def test_webhook_delivery(url: str, secret: str | None) -> dict:
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
