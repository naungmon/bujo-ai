"""Simple per-process rate limiter for AI API calls."""

import time
from threading import Lock


class RateLimiter:
    """Token-bucket rate limiter: max_calls per window_seconds."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._calls: list[float] = []
        self._lock = Lock()

    def acquire(self) -> bool:
        """Return True if the call is allowed, False if rate-limited."""
        with self._lock:
            now = time.monotonic()
            self._calls = [t for t in self._calls if now - t < self._window]
            if len(self._calls) < self._max:
                self._calls.append(now)
                return True
            return False

    def wait_and_acquire(self) -> None:
        """Block until a slot is available."""
        while not self.acquire():
            time.sleep(0.1)


_ai_limiter: RateLimiter | None = None


def get_ai_limiter() -> RateLimiter:
    global _ai_limiter
    if _ai_limiter is None:
        _ai_limiter = RateLimiter(max_calls=10, window_seconds=60.0)
    return _ai_limiter


def reset_for_testing() -> None:
    global _ai_limiter
    _ai_limiter = None
