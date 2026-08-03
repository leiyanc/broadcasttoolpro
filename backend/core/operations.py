import logging
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


LOGGER_NAME = "broadcast_tool_pro"


def configure_logging() -> logging.Logger:
    level_name = os.getenv("BTP_LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger(LOGGER_NAME)


@dataclass(frozen=True)
class RateLimitRule:
    requests: int
    window_seconds: int


SENSITIVE_RATE_LIMITS = {
    ("POST", "/api/auth/bootstrap"): RateLimitRule(3, 60 * 60),
    ("POST", "/api/auth/login"): RateLimitRule(10, 5 * 60),
    (
        "POST",
        "/api/auth/password-reset/request",
    ): RateLimitRule(5, 15 * 60),
    ("POST", "/api/auth/trial"): RateLimitRule(5, 60 * 60),
    (
        "POST",
        "/api/auth/access-requests",
    ): RateLimitRule(5, 60 * 60),
}


class RequestRateLimiter:
    """Process-local protection for the single-worker Stage 1 service."""

    def __init__(self, max_clients: int = 10_000):
        self.max_clients = max_clients
        self._requests: dict[
            tuple[str, str, str], deque[float]
        ] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(
        self,
        *,
        method: str,
        path: str,
        client_key: str,
        now: float | None = None,
    ) -> tuple[bool, int]:
        rule = SENSITIVE_RATE_LIMITS.get((method.upper(), path))
        if rule is None:
            return True, 0

        observed_at = time.monotonic() if now is None else now
        bucket_key = (client_key, method.upper(), path)
        cutoff = observed_at - rule.window_seconds

        with self._lock:
            if (
                bucket_key not in self._requests
                and len(self._requests) >= self.max_clients
            ):
                self._prune(observed_at)
                if len(self._requests) >= self.max_clients:
                    self._requests.pop(next(iter(self._requests)))
            bucket = self._requests[bucket_key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= rule.requests:
                retry_after = max(
                    1,
                    int(rule.window_seconds - (observed_at - bucket[0])) + 1,
                )
                return False, retry_after

            bucket.append(observed_at)
            return True, 0

    def _prune(self, now: float) -> None:
        longest_window = max(
            rule.window_seconds for rule in SENSITIVE_RATE_LIMITS.values()
        )
        cutoff = now - longest_window
        stale_keys = [
            key
            for key, bucket in self._requests.items()
            if not bucket or bucket[-1] <= cutoff
        ]
        for key in stale_keys:
            self._requests.pop(key, None)


logger = configure_logging()
request_rate_limiter = RequestRateLimiter()
