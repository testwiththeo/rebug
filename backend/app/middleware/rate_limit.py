"""Rate limiting middleware for API endpoints."""

import time
from typing import Optional

from app.core.config import get_settings
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis for distributed tracking."""

    def __init__(
        self,
        app,
        redis_client=None,
        max_requests: int = 10,
        window_seconds: int = 60,
        key_prefix: str = "ratelimit",
    ):
        super().__init__(app)
        self.redis_client = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/healthz", "/health"]:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_identifier(request)
        if not client_id:
            return await call_next(request)

        # Check rate limit
        if self.redis_client:
            allowed, retry_after = await self._check_rate_limit(
                client_id, request.url.path
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "RATE_LIMITED",
                        "message": f"Rate limit exceeded. Retry after {retry_after} seconds.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

        response = await call_next(request)
        return response

    def _get_client_identifier(self, request: Request) -> Optional[str]:
        """Extract client identifier from request."""
        # Try to get from Authorization header (API key)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return f"apikey:{auth_header[7:]}"

        # Fallback to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client = request.client
        if client:
            return f"ip:{client.host}"
        return None

    async def _check_rate_limit(self, client_id: str, path: str) -> tuple[bool, int]:
        """Check if request is within rate limit.

        Returns:
            Tuple of (allowed: bool, retry_after_seconds: int)
        """
        # Different limits for different endpoints
        if "/analyze" in path:
            max_requests = 5  # Stricter for AI analysis
            window = 60
        else:
            max_requests = self.max_requests
            window = self.window_seconds

        key = f"{self.key_prefix}:{client_id}:{path}"
        current_time = int(time.time())
        window_start = current_time - window

        try:
            # Remove expired entries
            await self.redis_client.zremrangebyscore(key, 0, window_start)

            # Count current requests
            count = await self.redis_client.zcard(key)

            if count >= max_requests:
                # Get oldest entry to calculate retry-after
                oldest = await self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1]) + window - current_time
                    return False, max(retry_after, 1)
                return False, window

            # Add current request
            await self.redis_client.zadd(key, {f"{current_time}": current_time})
            await self.redis_client.expire(key, window)

            return True, 0
        except Exception:
            # If Redis fails, allow request (fail open)
            return True, 0


async def get_redis_client():
    """Get Redis client for rate limiting."""
    import redis.asyncio as redis

    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def create_rate_limit_middleware(app, redis_client=None):
    """Create and configure rate limit middleware."""
    settings = get_settings()

    # Default limits
    max_requests = getattr(settings, "rate_limit_max_requests", 100)
    window_seconds = getattr(settings, "rate_limit_window_seconds", 60)

    if redis_client is None:
        redis_client = await get_redis_client()

    return RateLimitMiddleware(
        app,
        redis_client=redis_client,
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
