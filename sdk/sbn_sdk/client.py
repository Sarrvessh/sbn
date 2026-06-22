"""Non-blocking transport client for telemetry ingestion."""

from __future__ import annotations

import asyncio
import atexit
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from threading import Lock
from typing import Any

import httpx

from sbn_sdk.models import SpanPayload, TracePayload

logger = logging.getLogger(__name__)


class TraceIngestClient:
    """Send trace payloads to backend without blocking caller execution."""

    def __init__(
        self,
        base_url: str,
        ingest_path: str = "/api/v1/ingest",
        api_key: str | None = None,
        api_key_header_name: str = "X-API-Key",
        timeout_seconds: float = 2.0,
        max_workers: int = 4,
        max_retries: int = 2,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")

        self._base_url = base_url.rstrip("/")
        self._ingest_url = f"{self._base_url}{ingest_path}"
        self._spans_url = f"{self._base_url}/api/v1/traces"
        self._span_update_url = f"{self._base_url}/api/v1/spans"
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._headers = (
            {api_key_header_name: api_key}
            if api_key is not None
            else None
        )
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="sbn-trace-sender",
        )
        self._futures: set[Future[None]] = set()
        self._lock = Lock()

    def send_non_blocking(self, payload: TracePayload) -> None:
        """Schedule payload delivery on a background worker thread."""

        payload_dict = payload.model_dump(mode="json")
        future = self._executor.submit(self._send_with_retries, payload_dict)
        with self._lock:
            self._futures.add(future)
        future.add_done_callback(self._cleanup_future)

    async def send_async(self, payload: TracePayload) -> None:
        """Asynchronously send payload from an async event loop context."""

        payload_dict = payload.model_dump(mode="json")
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            for attempt in range(1, self._max_retries + 1):
                try:
                    response = await client.post(
                        self._ingest_url,
                        json=payload_dict,
                        headers=self._headers,
                    )
                    response.raise_for_status()
                    return
                except httpx.HTTPError as exc:
                    if attempt == self._max_retries:
                        logger.warning("Failed to send trace asynchronously: %s", exc)
                        return
                    await asyncio.sleep(0.1 * attempt)

    def _send_with_retries(self, payload_dict: dict[str, Any]) -> None:
        """Send payload with lightweight retry strategy."""

        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(
                        self._ingest_url,
                        json=payload_dict,
                        headers=self._headers,
                    )
                    response.raise_for_status()
                return
            except httpx.HTTPError as exc:
                if attempt == self._max_retries:
                    logger.warning("Failed to send trace in background thread: %s", exc)
                    return
                time.sleep(0.1 * attempt)

    def _cleanup_future(self, future: Future[None]) -> None:
        """Drop completed futures and suppress handled exceptions."""

        with self._lock:
            self._futures.discard(future)

        try:
            future.result()
        except Exception as exc:  # pragma: no cover
            logger.warning("Trace sender future completed with exception: %s", exc)

    def send_span_non_blocking(self, payload: SpanPayload) -> None:
        """Schedule span creation on a background worker thread."""
        payload_dict = payload.model_dump(mode="json", exclude_none=True)
        payload_dict["started_at"] = payload.started_at.isoformat()
        payload_dict["ended_at"] = payload.ended_at.isoformat() if payload.ended_at else None
        url = f"{self._spans_url}/{payload.trace_request_id}/spans"
        future = self._executor.submit(self._send_post, url, payload_dict)
        with self._lock:
            self._futures.add(future)
        future.add_done_callback(self._cleanup_future)

    def send_span_finalize_non_blocking(
        self,
        span_id: str,
        output: str,
        total_tokens: int,
        cost: float,
        status_code: str,
        status_message: str,
        started_at: datetime,
        ended_at: datetime,
        latency_ms: float,
    ) -> None:
        """Schedule span finalization on a background worker thread."""
        payload_dict = {
            "output": output,
            "total_tokens": total_tokens,
            "cost": cost,
            "status_code": status_code,
            "status_message": status_message,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "latency_ms": latency_ms,
        }
        url = f"{self._span_update_url}/{span_id}"
        future = self._executor.submit(self._send_patch, url, payload_dict)
        with self._lock:
            self._futures.add(future)
        future.add_done_callback(self._cleanup_future)

    def _send_post(self, url: str, payload_dict: dict[str, Any]) -> None:
        """Send a POST request with retries."""
        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.post(url, json=payload_dict, headers=self._headers)
                    response.raise_for_status()
                return
            except httpx.HTTPError as exc:
                if attempt == self._max_retries:
                    logger.warning("Failed to POST %s: %s", url, exc)
                    return
                time.sleep(0.1 * attempt)

    def _send_patch(self, url: str, payload_dict: dict[str, Any]) -> None:
        """Send a PATCH request with retries."""
        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.patch(url, json=payload_dict, headers=self._headers)
                    response.raise_for_status()
                return
            except httpx.HTTPError as exc:
                if attempt == self._max_retries:
                    logger.warning("Failed to PATCH %s: %s", url, exc)
                    return
                time.sleep(0.1 * attempt)

    def shutdown(self, wait: bool = True) -> None:
        """Release worker resources."""

        self._executor.shutdown(wait=wait, cancel_futures=False)


_CLIENT_REGISTRY: dict[str, TraceIngestClient] = {}
_CLIENT_REGISTRY_LOCK = Lock()


def get_or_create_client(base_url: str, api_key: str | None = None) -> TraceIngestClient:
    """Return a singleton client per backend base URL."""

    base = base_url.rstrip("/")
    key = f"{base}|{api_key or ''}"
    with _CLIENT_REGISTRY_LOCK:
        existing = _CLIENT_REGISTRY.get(key)
        if existing is not None:
            return existing

        created = TraceIngestClient(base_url=base, api_key=api_key)
        _CLIENT_REGISTRY[key] = created
        return created


def shutdown_all_clients() -> None:
    """Shutdown all cached clients on process exit."""

    with _CLIENT_REGISTRY_LOCK:
        clients = list(_CLIENT_REGISTRY.values())
        _CLIENT_REGISTRY.clear()

    for client in clients:
        client.shutdown()


atexit.register(shutdown_all_clients)
