"""
Monitoring middleware for request/response tracking.

Records:
- Request duration
- HTTP status codes
- Request/response sizes
- Error rates
"""

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.monitoring.logging import get_logger
from app.monitoring.metrics import (
    record_http_request,
    record_api_error,
)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response monitoring.

    Records:
    - Request duration
    - HTTP status codes
    - Request/response sizes
    - Error rates
    """

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.excluded_paths = excluded_paths or ["/health", "/metrics", "/favicon.ico"]
        self.logger = get_logger("app.http")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip monitoring for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Generate correlation ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])

        # Start timing
        start_time = time.perf_counter()

        # Get request size
        request_size = 0
        if request.headers.get("content-length"):
            try:
                request_size = int(request.headers["content-length"])
            except ValueError:
                pass

        # Process request
        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            # Get response size
            response_size = 0
            if response.headers.get("content-length"):
                try:
                    response_size = int(response.headers["content-length"])
                except ValueError:
                    pass

            # Record metrics
            record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size,
            )

            # Add correlation ID to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

            return response

        except Exception as exc:
            duration = time.perf_counter() - start_time
            record_api_error(
                endpoint=request.url.path,
                error_type=type(exc).__name__,
            )
            raise


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to request state."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract correlation ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])

        # Add to request state for use in route handlers
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS for production
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request logging."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("app.request")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", str(uuid.uuid4())[:8])

        # Log request
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            self.logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            return response

        except Exception as exc:
            duration = time.perf_counter() - start_time
            self.logger.exception(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(exc),
                duration_ms=round(duration * 1000, 2),
            )
            raise