"""FastAPI entrypoint for AI observability backend."""

from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager
from typing import AsyncIterator

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse, PlainTextResponse

from app.api.v1.router import api_router
from app.core.config import get_cors_origins, settings
from app.core.logging_config import configure_logging
from app.core.middleware import RequestTimingMiddleware
from app.db.init_db import backfill_projects, initialize_database
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


def _run_migrations() -> None:
    try:
        alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully")
    except Exception as exc:
        logger.warning("Failed to run migrations (may be acceptable if tables already exist): %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    _validate_prod_settings()
    _run_migrations()
    initialize_database()
    backfill_projects()
    yield


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    if settings.enforce_trusted_hosts:
        allowed_hosts = [h.strip() for h in settings.trusted_hosts.split(",") if h.strip()]
        application.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts,
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
        from app.db.session import SessionLocal
        try:
            db = SessionLocal()
            db.execute(db.bind.dialect.statement_compiler(db.bind.dialect, None).__class__)
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

    return application


app = create_application()