"""Tests for the in-memory TTL cache."""

from __future__ import annotations

import time

from app.services.cache_service import TTLCache


class TestTTLCache:
    def test_set_and_get(self):
        cache = TTLCache(default_ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_missing_key(self):
        cache = TTLCache(default_ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_expiry(self):
        cache = TTLCache(default_ttl_seconds=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_custom_ttl(self):
        cache = TTLCache(default_ttl_seconds=60)
        cache.set("key1", "value1", ttl_seconds=2)
        assert cache.get("key1") == "value1"
        time.sleep(2.1)
        assert cache.get("key1") is None

    def test_invalidate(self):
        cache = TTLCache(default_ttl_seconds=60)
        cache.set("key1", "value1")
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_clear(self):
        cache = TTLCache(default_ttl_seconds=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_overwrite(self):
        cache = TTLCache(default_ttl_seconds=60)
        cache.set("key1", "value1")
        cache.set("key1", "value2")
        assert cache.get("key1") == "value2"

    def test_none_value(self):
        cache = TTLCache(default_ttl_seconds=60)
        cache.set("key1", None)
        assert cache.get("key1") is None
