"""A tiny thread-safe in-memory TTL cache.

Deliberately minimal — no Redis, no DB. The FPL API is the source of truth; this
just avoids refetching the same large payloads (bootstrap-static, fixtures) on
every request. Entries expire after `ttl` seconds and are refetched on the next
access. Cache is per-process, so it's lost on restart/cold start (fine — it just
re-warms on the first request).
"""
import threading
import time
from typing import Any, Callable, Dict, Tuple

_lock = threading.Lock()
_store: Dict[str, Tuple[float, Any]] = {}  # key -> (expires_at_epoch, value)


def get_or_set(key: str, ttl: float, producer: Callable[[], Any]) -> Any:
    """Return the cached value for `key`, or call `producer()` and cache it.

    `producer` runs outside the lock so a slow network fetch never blocks other
    keys. Two racers on a cold key may both fetch once; that's cheap and rare,
    and avoids holding the lock across I/O.
    """
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if entry and entry[0] > now:
            return entry[1]

    value = producer()  # cache miss — fetch outside the lock

    with _lock:
        _store[key] = (time.time() + ttl, value)
    return value


def invalidate(key: str | None = None) -> None:
    """Drop one key, or the whole cache when `key` is None."""
    with _lock:
        if key is None:
            _store.clear()
        else:
            _store.pop(key, None)
