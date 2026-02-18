from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


class DataCache:
    """
    Simple in-memory cache with per-key TTL support.
    Stores small payloads (dicts/tuples) for data sources such as weather, stocks, etc.
    """

    def __init__(self, logger=None):
        self._entries: Dict[str, CacheEntry] = {}
        self.logger = logger

    def get(
        self,
        key: str,
        fetcher: Callable[[], Any],
        ttl_seconds: int,
        allow_stale: bool = True,
    ) -> Any:
        now = datetime.utcnow()
        entry = self._entries.get(key)
        if entry and entry.expires_at > now:
            return entry.value

        try:
            value = fetcher()
        except Exception as exc:  # pragma: no cover - network/IO
            if self.logger:
                self.logger.warning("Cache fetch for %s failed: %s", key, exc)
            if allow_stale and entry:
                return entry.value
            raise

        self._entries[key] = CacheEntry(
            value=value, expires_at=now + timedelta(seconds=max(ttl_seconds, 1))
        )
        return value

    def clear(self, key: Optional[str] = None):
        if key:
            self._entries.pop(key, None)
        else:
            self._entries.clear()
