"""FastAPI entrypoint for AI observability backend."""

from __future__ import annotations

import logging
import os
import traceback
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse, PlainTextResponse

from app.api.v1.router import api_router
from app.core.config import get_cors_origins, settings
from app.core.logging_config import configure_logging
from app.core.middleware import RequestTimingMiddleware
from app.db.init_db import initialize_database
from app.services.metrics_service import registry

logger = logging.getLogger("app")


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    enabled=settings.rate_limit_enabled,
    storage_uri="memory://",
)


def _validate_prod_settings() -> None:
    errors = settings.validate_required_for_prod()
    for error in errors:
        logger.warning("Production configuration warning: %s", error)


def _initialize_app() -> None:
    import time as _time
    _validate_prod_settings()
    try:
        t0 = _time.time()
        initialize_database()
        logger.info("DB init done in %.2fs", _time.time() - t0)
    except Exception:
        logger.exception("App initialization failed — continuing")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    import time as _time
    t0 = _time.time()
    configure_logging()
    logger.info("App startup started")
    _initialize_app()
    logger.info("App startup complete in %.2fs", _time.time() - t0)
    yield
    logger.info("App shutting down")


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestTimingMiddleware)

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.exception_handler(RequestValidationError)
    @application.exception_handler(ValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError | ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation failed", "errors": exc.errors() if hasattr(exc, "errors") else str(exc)},
        )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @application.get("/health", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/readyz", tags=["health"])
    async def readiness() -> JSONResponse:
        from sqlalchemy import text

        from app.db.session import SessionLocal
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable", "detail": "database unreachable"})
        return JSONResponse(content={"status": "ready"})

    @application.get("/livez", tags=["health"])
    async def liveness() -> dict[str, str]:
        return {"status": "alive"}

    @application.get("/metrics", tags=["metrics"])
    def metrics() -> PlainTextResponse:
        return PlainTextResponse(
            content=registry.collect_all(),
            media_type="text/plain; version=0.0.4",
            headers={"Cache-Control": "no-cache"},
        )

    frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    if os.path.isdir(frontend_dist):
        application.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    else:
        logger.warning("Frontend dist not found at %s — serving API only", frontend_dist)

    return application


app = create_application()
