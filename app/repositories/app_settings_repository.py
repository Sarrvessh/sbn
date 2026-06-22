from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppSetting


class AppSettingsRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create(self) -> AppSetting:
        setting = self._db.scalar(select(AppSetting).limit(1))
        if setting is None:
            setting = AppSetting()
            self._db.add(setting)
            self._db.flush()
        return setting

    def update(self, payload: dict) -> AppSetting:
        setting = self.get_or_create()
        for key, value in payload.items():
            if value is not None and hasattr(setting, key):
                setattr(setting, key, value)
        self._db.commit()
        self._db.refresh(setting)
        return setting
