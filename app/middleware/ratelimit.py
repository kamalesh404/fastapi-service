"""
Rate limiting middleware with Redis backend.

Provides configurable rate limiting per IP, user, or custom key.
"""

import time
from typing import Callable, Optional, Tuple

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

import redis.asyncio as redis

from app.core.config import settings
from app.monitoring.metrics import record_api_error


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with Redis backend.

    Features:
    - Per-IP, per-user, or custom key limiting
    - Sliding window algorithm
    - Configurable limits and windows
    - Header-based rate limit info
    - Exempt paths configuration
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        key_func: Optional[Callable[[Request], str]] = None,
        exempt_paths: Optional[list[str]] = None,
        redis_url: Optional[str] = None,
    ):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
        self.exempt_paths = exempt_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        self.redis_url = redis_url or settings.REDIS_URL

        # Initialize Redis connection pool
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    def _default_key_func(self, request: Request) -> str:
        """Default key function: IP-based limiting."""
        client_host = request.client.host if request.client else "unknown"
        # Include path for per-endpoint limiting
        return f"ratelimit:{client_host}:{request.url.path}"

    def _get_window_key(self, key: str) -> Tuple[str, int]:
        """Generate Redis key and window timestamp."""
        current_window = int(time.time() // self.window_seconds)
        window_key = f"{key}:{current_window}"
        return window_key, current_window

    async def _check_rate_limit(self, key: str) -> Tuple[bool, int, int]:
        """
        Check rate limit using sliding window.

        Returns:
            (allowed, current_count, remaining)
        """
        redis_client = await self._get_redis()
        window_key, window = self._get_window_key(key)

        # Use Redis pipeline for atomic operations
        pipe = redis_client.pipeline()

        # Increment counter
        pipe.incr(window_key)
        # Set expiry
        pipe.expire(window_key, self.window_seconds + 1)
        # Get current count
        pipe.get(window_key)

        results = await pipe.execute()
        current_count = results[2]

        # Check if limit exceeded
        allowed = current_count <= self.requests_per_window
        remaining = max(0, self.requests_per_window - current_count)

        return allowed, current_count, remaining

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Skip if rate limiting disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get rate limit key
        try:
            key = self.key_func(request)
        except Exception:
            # If key function fails, allow request
            return await call_next(request)

        # Check rate limit
        try:
            allowed, current_count, remaining = await self._check_rate_limit(key)

            if not allowed:
                # Rate limit exceeded
                record_api_error(
                    endpoint=request.url.path,
                    error_type="rate_limit_exceeded",
                )

                retry_after = self.window_seconds - int(time.time() % self.window_seconds)

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={
                        "X-RateLimit-Limit": str(self.requests_per_window),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + self.window_seconds),
                        "Retry-After": str(retry_after),
                    },
                )

            # Add rate limit headers
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_seconds)

            return response

        except HTTPException:
            raise
        except Exception:
            # If Redis fails, allow request (fail open)
            return await call_next(request)


class UserRateLimitMiddleware(RateLimitMiddleware):
    """
    User-based rate limiting.

    Uses authenticated user ID as key instead of IP.
    """

    def _default_key_func(self, request: Request) -> str:
        """Use user ID if authenticated, otherwise IP."""
        # Check if user is authenticated (from auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"ratelimit:user:{user_id}:{request.url.path}"

        # Fallback to IP
        return super()._default_key_func(request)


def create_rate_limiter(
    requests: int = 100,
    window: int = 60,
    key_func: Optional[Callable] = None,
) -> RateLimitMiddleware:
    """Factory function for creating rate limiters."""
    return RateLimitMiddleware(
        app=None,  # Will be set by FastAPI
        requests_per_window=requests,
        window_seconds=window,
        key_func=key_func,
    )