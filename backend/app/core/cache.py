"""Small in-process TTL cache for lookups against external catalogues.

Enough for one API process: the point is not to hit ASF / USGS / POWER / FIRMS
again when the map re-asks for the same place a moment later. Failures are
never cached.
"""

import threading
import time
from collections.abc import Callable
from typing import Any

_MAX_ENTRIES = 256
_entries: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


def cached(key: str, ttl: float, produce: Callable[[], Any]) -> Any:
    now = time.monotonic()
    with _lock:
        hit = _entries.get(key)
        if hit is not None and hit[0] > now:
            return hit[1]
    value = produce()  # outside the lock: these calls take seconds
    if ttl > 0:
        with _lock:
            if len(_entries) >= _MAX_ENTRIES:
                for stale in [k for k, (expires, _) in _entries.items() if expires <= now]:
                    del _entries[stale]
                if len(_entries) >= _MAX_ENTRIES:
                    _entries.pop(next(iter(_entries)))
            _entries[key] = (now + ttl, value)
    return value


def clear() -> None:
    with _lock:
        _entries.clear()
