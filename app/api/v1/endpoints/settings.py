from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import Principal, require_roles
from app.db.session import get_db
from app.repositories.app_settings_repository import AppSettingsRepository
from app.schemas.settings import AppSettingsResponse, AppSettingsUpdate

router = APIRouter(prefix="")


@router.get("/settings", response_model=AppSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> AppSettingsResponse:
    repo = AppSettingsRepository(db)
    setting = repo.get_or_create()
    return AppSettingsResponse.model_validate(setting)


@router.put("/settings", response_model=AppSettingsResponse)
def update_settings(
    payload: AppSettingsUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_roles("admin")),
) -> AppSettingsResponse:
    repo = AppSettingsRepository(db)
    updated = repo.update(payload.model_dump(exclude_none=True))
    return AppSettingsResponse.model_validate(updated)
