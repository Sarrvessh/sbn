"""Authentication and authorization dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.repositories.api_key_repository import ApiKeyRepository, hash_api_key

_ALLOWED_ROLES = {"admin", "analyst", "viewer", "ingest"}


@dataclass(slots=True)
class Principal:
    """Authenticated principal derived from API key."""

    role: str
    key_prefix: str
    project_scope: str | None
    project_scopes: tuple[str, ...] | None


def get_current_principal(
    request: Request,
    db: Session = Depends(get_db),
) -> Principal:
    """Authenticate request using configured API key header."""

    provided_key = request.headers.get(settings.api_key_header_name)
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing API key in header {settings.api_key_header_name}",
        )

    repository = ApiKeyRepository(db)
    record = repository.get_active_by_hash(hash_api_key(provided_key))
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    parsed_scopes = _parse_project_scopes(record.project_scope)
    return Principal(
        role=record.role,
        key_prefix=record.key_prefix,
        project_scope=record.project_scope,
        project_scopes=parsed_scopes,
    )


def require_roles(*allowed_roles: str):
    """Build dependency enforcing RBAC role checks with admin override."""

    roles = set(allowed_roles)
    if not roles.issubset(_ALLOWED_ROLES):
        invalid_roles = roles.difference(_ALLOWED_ROLES)
        raise ValueError(f"Invalid roles configured: {sorted(invalid_roles)}")

    def _role_dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role == "admin":
            return principal
        if principal.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return principal

    return _role_dependency


def resolve_project_scope(principal: Principal, requested_project: str | None) -> str | None:
    """Resolve a single project target for write-style operations."""

    if principal.project_scopes is None:
        return requested_project

    if requested_project is None and len(principal.project_scopes) == 1:
        return principal.project_scopes[0]

    if requested_project is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_name is required because this API key spans multiple projects",
        )

    if requested_project not in principal.project_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requested project is outside API key scope",
        )

    return requested_project


def resolve_project_scopes(
    principal: Principal,
    requested_project: str | None,
) -> list[str] | None:
    """Resolve one or many allowed projects for read-style operations."""

    if principal.project_scopes is None:
        if requested_project is None:
            return None
        return [requested_project]

    if requested_project is None:
        return list(principal.project_scopes)

    if requested_project not in principal.project_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requested project is outside API key scope",
        )

    return [requested_project]


def _parse_project_scopes(project_scope: str | None) -> tuple[str, ...] | None:
    """Parse comma-separated project scope values into canonical tuple."""

    if project_scope is None:
        return None

    normalized_scope = project_scope.strip()
    if not normalized_scope:
        return None

    raw_tokens = normalized_scope.replace(";", ",").split(",")
    cleaned_tokens = [item.strip() for item in raw_tokens if item.strip()]
    if not cleaned_tokens:
        return None

    # Preserve declaration order while removing accidental duplicates.
    deduped = tuple(dict.fromkeys(cleaned_tokens))
    return deduped
