"""Admin endpoints for API key lifecycle management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.session import get_db
from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.auth import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyInfoResponse,
)

router = APIRouter(prefix="")


@router.get("/auth/api-keys", response_model=list[ApiKeyInfoResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> list[ApiKeyInfoResponse]:
    """List API key metadata for administrative operations."""

    repository = ApiKeyRepository(db)
    records = repository.list_all()
    return [
        ApiKeyInfoResponse(
            key_prefix=item.key_prefix,
            role=item.role,
            project_scope=item.project_scope,
            description=item.description,
            is_active=item.is_active,
            created_at=item.created_at,
        )
        for item in records
    ]


@router.post("/auth/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    request: ApiKeyCreateRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> ApiKeyCreateResponse:
    """Create a new API key with optional project scope and role."""

    if request.role == "admin" and request.project_scope is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin keys cannot be project scoped",
        )

    repository = ApiKeyRepository(db)
    try:
        record, raw_key = repository.create_api_key(
            role=request.role,
            project_scope=request.project_scope,
            description=request.description,
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key",
        ) from exc

    return ApiKeyCreateResponse(
        api_key=raw_key,
        key_prefix=record.key_prefix,
        role=record.role,
        project_scope=record.project_scope,
        description=record.description,
        is_active=record.is_active,
        created_at=record.created_at,
    )
