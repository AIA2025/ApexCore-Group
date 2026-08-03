import time
from collections import defaultdict
from fastapi import Request


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.calls = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self.calls[key] = [t for t in self.calls[key] if t > cutoff]
        if len(self.calls[key]) < self.max_requests:
            self.calls[key].append(now)
            return True
        return False


checkout_limiter = InMemoryRateLimiter(8, 60)
login_limiter = InMemoryRateLimiter(10, 60)
