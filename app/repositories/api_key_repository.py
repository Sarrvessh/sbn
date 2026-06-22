"""Data access helpers for API key records."""

from __future__ import annotations

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ApiKey


class ApiKeyRepository:
    """Repository for API key lookup and bootstrap provisioning."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active_by_hash(self, api_key_hash: str) -> ApiKey | None:
        """Return active API key matching a hashed value."""

        statement = select(ApiKey).where(
            ApiKey.key_hash == api_key_hash,
            ApiKey.is_active.is_(True),
        )
        return self._db.scalar(statement)

    def upsert_bootstrap_key(
        self,
        api_key: str,
        role: str,
        project_scope: str | None,
        description: str,
    ) -> ApiKey:
        """Create or update bootstrap API key records."""

        key_hash = hash_api_key(api_key)
        key_prefix = key_hash[:12]

        existing = self._db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
        if existing is None:
            existing = ApiKey(
                key_prefix=key_prefix,
                key_hash=key_hash,
                role=role,
                project_scope=project_scope,
                description=description,
                is_active=True,
            )
            self._db.add(existing)
        else:
            existing.key_prefix = key_prefix
            existing.role = role
            existing.project_scope = project_scope
            existing.description = description
            existing.is_active = True

        return existing

    def list_all(self) -> list[ApiKey]:
        """Return all API key records ordered by latest first."""

        statement = select(ApiKey).order_by(ApiKey.created_at.desc())
        return list(self._db.scalars(statement).all())

    def create_api_key(
        self,
        role: str,
        project_scope: str | None,
        description: str | None,
    ) -> tuple[ApiKey, str]:
        """Generate and persist a new API key record."""

        for _ in range(5):
            raw_key = f"sbn_{role}_{secrets.token_urlsafe(32)}"
            key_hash = hash_api_key(raw_key)
            existing = self._db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
            if existing is not None:
                continue

            record = ApiKey(
                key_prefix=key_hash[:12],
                key_hash=key_hash,
                role=role,
                project_scope=project_scope,
                description=description,
                is_active=True,
            )
            self._db.add(record)
            self._db.flush()
            self._db.refresh(record)
            return record, raw_key

        raise RuntimeError("Unable to generate a unique API key")


def hash_api_key(api_key: str) -> str:
    """Return deterministic SHA-256 hash for API key secrets."""

    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
