import time
from typing import Optional

from app.config import config


_RATE_LIMIT_PATTERNS = (
    "429",
    "quota exceeded",
    "exceeded your current quota",
    "resource_exhausted",
    "rate_limit_exceeded",
    "rate limit",
    "too many requests",
    "insufficient_quota",
    "quota_exceeded",
)


class ApiKeyPool:
    def __init__(self, keys: list[str], cooldown_seconds: float = 300.0):
        self.keys = [key.strip() for key in keys if key and key.strip()]
        self.cooldown_seconds = cooldown_seconds
        self._next_index = 0
        self._cooldowns: dict[str, float] = {}

    @classmethod
    def from_config(cls, service_name: str) -> Optional["ApiKeyPool"]:
        multi_key_name = f"{service_name}_api_keys"
        single_key_name = f"{service_name}_api_key"
        keys = _parse_api_keys(config.app.get(multi_key_name, []))
        if not keys:
            keys = _parse_api_keys(config.app.get(single_key_name, ""))
        if not keys:
            return None

        cooldown_seconds = float(config.app.get("api_key_cooldown_seconds", 300) or 300)
        return cls(keys, cooldown_seconds=cooldown_seconds)

    @property
    def max_attempts(self) -> int:
        return max(len(self.keys), 1)

    def get(self) -> Optional[str]:
        if not self.keys:
            return None

        self._clear_expired_cooldowns()
        for _ in range(len(self.keys)):
            key = self.keys[self._next_index]
            self._next_index = (self._next_index + 1) % len(self.keys)
            if key not in self._cooldowns:
                return key
        return None

    def mark_rate_limited(self, key: str) -> None:
        if not key:
            return
        self._cooldowns[key] = time.monotonic() + self.cooldown_seconds

    def _clear_expired_cooldowns(self) -> None:
        now = time.monotonic()
        expired = [key for key, until in self._cooldowns.items() if until <= now]
        for key in expired:
            del self._cooldowns[key]


def _parse_api_keys(value) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple)):
        keys: list[str] = []
        for item in value:
            if isinstance(item, str):
                keys.extend(_parse_api_keys(item))
        return keys
    return []


def is_rate_limit_error(error: BaseException) -> bool:
    text = str(error).lower()
    return any(pattern in text for pattern in _RATE_LIMIT_PATTERNS)


def mask_key_label(key: str, keys: list[str]) -> str:
    try:
        index = keys.index(key) + 1
    except ValueError:
        index = 0
    return f"key #{index}" if index else "unknown key"


_API_KEY_POOLS: dict[str, ApiKeyPool] = {}


def get_api_key_pool(service_name: str) -> Optional[ApiKeyPool]:
    pool = _API_KEY_POOLS.get(service_name)
    if pool is None:
        pool = ApiKeyPool.from_config(service_name)
        if pool is not None:
            _API_KEY_POOLS[service_name] = pool
    return pool


def reset_api_key_pools() -> None:
    _API_KEY_POOLS.clear()
