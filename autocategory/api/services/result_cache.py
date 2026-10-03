"""Bounded TTL cache, shared Redis results and per-worker request coalescing.

Keys contain hashes, never source text. JSON copies prevent callers from mutating
cached values. Redis failures fall back to memory; failures from producers are
never cached. Taxonomy versions live in PostgreSQL, independently of Redis.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from contextvars import ContextVar
from typing import Any, Callable

from config import settings
from services.metrics_service import record_cache_hit, record_cache_miss

logger = logging.getLogger(__name__)
SCHEMA_VERSION = "ac-cache-v1"
_attempt: ContextVar[dict | None] = ContextVar("cache_attempt", default=None)


def mark_uncacheable() -> None:
    """Keep graceful fallbacks usable without storing transient partial results."""
    attempt = _attempt.get()
    if attempt is not None:
        attempt["failed"] = True


def digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


class ResultCache:
    def __init__(self, max_entries: int = 512, max_bytes: int = 16777216):
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.redis = None
        self._memory: OrderedDict[str, tuple[float, str, int]] = OrderedDict()
        self._bytes = 0
        self._flights: dict[tuple, asyncio.Task] = {}

    def clear_local(self) -> None:
        self._memory.clear()
        self._bytes = 0

    def _remember(self, key: str, payload: str, ttl: float) -> None:
        size = len(payload.encode())
        if size > self.max_bytes or self.max_entries <= 0 or ttl <= 0:
            return
        previous = self._memory.pop(key, None)
        if previous:
            self._bytes -= previous[2]
        self._memory[key] = (time.monotonic() + ttl, payload, size)
        self._bytes += size
        while len(self._memory) > self.max_entries or self._bytes > self.max_bytes:
            self._bytes -= self._memory.popitem(last=False)[1][2]

    async def _read(self, key: str, ttl: int) -> str | None:
        entry = self._memory.get(key)
        if entry:
            if entry[0] > time.monotonic():
                self._memory.move_to_end(key)
                return entry[1]
            self._bytes -= self._memory.pop(key)[2]
        if self.redis is not None:
            try:
                # Preserve the shared entry's remaining TTL in the memory tier.
                async with self.redis.pipeline(transaction=False) as pipe:
                    payload, remaining_ms = await asyncio.wait_for(
                        pipe.get(key).pttl(key).execute(), timeout=0.5,
                    )
                if payload is not None and remaining_ms > 0:
                    if isinstance(payload, bytes):
                        payload = payload.decode()
                    json.loads(payload)  # Ignore malformed shared entries.
                    self._remember(key, payload, min(ttl, remaining_ms / 1000))
                    return payload
            except Exception as exc:
                logger.debug("Result cache read unavailable: %s", type(exc).__name__)
        return None

    async def get_or_compute(self, namespace: str, identity: Any, ttl: int,
                             producer: Callable, *, enabled: bool = True,
                             cacheable: Callable = lambda value: value is not None) -> Any:
        if not settings.cache_enabled or not enabled or ttl <= 0:
            return await producer()
        key = f"{namespace}:{SCHEMA_VERSION}:{digest(identity)}"
        payload = await self._read(key, ttl)
        if payload is not None:
            record_cache_hit(namespace)
            return json.loads(payload)
        flight_key = (asyncio.get_running_loop(), key)
        task = self._flights.get(flight_key)
        if task is None:
            record_cache_miss(namespace)

            async def produce():
                attempt = {"failed": False}
                token = _attempt.set(attempt)
                try:
                    value = await producer()
                    if not attempt["failed"] and cacheable(value):
                        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                        self._remember(key, encoded, ttl)
                        if self.redis is not None:
                            try:
                                await asyncio.wait_for(self.redis.set(key, encoded, ex=ttl), timeout=0.5)
                            except Exception as exc:
                                logger.debug("Result cache write unavailable: %s", type(exc).__name__)
                    return value, attempt["failed"]
                finally:
                    _attempt.reset(token)

            task = asyncio.create_task(produce())
            self._flights[flight_key] = task

            def finished(done):
                self._flights.pop(flight_key, None)
                # Retrieve exceptions even if all waiting requests disconnected.
                if not done.cancelled():
                    done.exception()

            task.add_done_callback(finished)
        else:
            record_cache_hit(namespace)
        value, failed = await asyncio.shield(task)
        if failed:
            mark_uncacheable()
        return json.loads(json.dumps(value, ensure_ascii=False))


cache = ResultCache(settings.cache_memory_entries, settings.cache_memory_bytes)


async def taxonomy_version() -> str | None:
    """Read the authoritative revision without holding a connection over awaits.

    If PostgreSQL is unavailable, bypass taxonomy-sensitive caches rather than
    reusing a revision that might have changed in another worker.
    """
    if not settings.cache_enabled:
        return None
    def load():
        from database import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            row = db.execute(text("SELECT value FROM system_config WHERE key = 'cache.taxonomy_version'"))
            return row.scalar() or "initial"
    try:
        return await asyncio.to_thread(load)
    except Exception as exc:
        logger.debug("Taxonomy revision unavailable: %s", type(exc).__name__)
        return None


async def invalidate_taxonomy() -> None:
    def update():
        from database import SessionLocal, bump_taxonomy_revision
        with SessionLocal() as db:
            bump_taxonomy_revision(db)
            db.commit()
    await asyncio.to_thread(update)
    cache.clear_local()
