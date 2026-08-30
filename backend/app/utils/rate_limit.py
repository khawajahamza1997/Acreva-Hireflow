import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request

# In-memory fixed-window limiter. Deliberately simple: this app deploys as a single
# Render web instance today, so a per-process dict is enough. If it ever scales to
# multiple instances, this needs a shared store (Redis) instead — noted, not built,
# since that infrastructure doesn't exist yet and isn't justified at current scale.
_hits: dict[str, deque] = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, bucket: str, limit: int, window_seconds: int = 60) -> None:
    key = f"{bucket}:{_client_key(request)}"
    now = time.monotonic()
    window = _hits[key]
    while window and now - window[0] > window_seconds:
        window.popleft()
    if len(window) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down and try again shortly.")
    window.append(now)


def rate_limiter(bucket: str, limit: int, window_seconds: int = 60):
    """FastAPI dependency factory: Depends(rate_limiter("upload", settings.rate_limit_upload_per_minute))"""

    def dependency(request: Request) -> None:
        enforce_rate_limit(request, bucket, limit, window_seconds)

    return dependency
