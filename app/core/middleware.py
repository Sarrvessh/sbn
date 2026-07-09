from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.services.metrics_service import http_request_duration_seconds, http_requests_total

logger = logging.getLogger("app.middleware")

_REQUEST_ID_HEADER = "X-Request-ID"
_EXCLUDE_PATHS = {"/metrics", "/health"}


class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get(_REQUEST_ID_HEADER, uuid.uuid4().hex)
        request.state.request_id = request_id

        if request.url.path in _EXCLUDE_PATHS:
            response = await call_next(request)
            response.headers[_REQUEST_ID_HEADER] = request_id
            return response

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        duration_sec = duration_ms / 1000
        response.headers["X-Response-Time-Ms"] = str(round(duration_ms, 2))
        response.headers[_REQUEST_ID_HEADER] = request_id

        http_requests_total.inc({"method": request.method, "path": request.url.path, "status": str(response.status_code)})
        http_request_duration_seconds.observe(duration_sec, {"method": request.method, "path": request.url.path})

        logger.info(
            "[%s] %s %s %d %.2fms",
            request_id, request.method, request.url.path, response.status_code, duration_ms,
        )
        return response