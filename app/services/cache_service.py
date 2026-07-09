from __future__ import annotations

import time
from threading import Lock


class TTLCache:
    """Simple thread-safe in-memory TTL cache. No Redis needed."""

    def __init__(self, default_ttl_seconds: int = 30) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, tuple[float, object]] = {}
        self._lock = Lock()

    def get(self, key: str) -> object | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        with self._lock:
            self._store[key] = (time.monotonic() + ttl, value)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


metrics_cache = TTLCache(default_ttl_seconds=30)
