"""
FastAPI Service - Main Application Entry Point.

Production-ready FastAPI application with:
- Complete authentication system
- Database migrations
- Monitoring & metrics
- Rate limiting
- CORS & security
- Health checks
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest

from app.api.router import api_router
from app.core.config import settings
from app.db.session import db_manager
from app.middleware.monitoring import (
    MonitoringMiddleware,
    CorrelationIDMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
)
from app.middleware.ratelimit import RateLimitMiddleware
from app.monitoring.logging import setup_logging, get_logger
from app.monitoring.metrics import metrics_endpoint
from app.services.cache import cache_service
from app.services.storage import storage_service
from app.services.celery import celery_app

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting FastAPI Service", version=settings.APP_VERSION)

    # Initialize database
    db_manager.initialize()
    await db_manager.initialize()
    logger.info("Database initialized")

    # Initialize cache
    await cache_service.connect()
    logger.info("Cache service connected")

    # Initialize storage
    # Storage service is auto-initialized
    logger.info("Storage service initialized")

    # Initialize Celery (if needed)
    # celery_app.conf.update(...) already configured

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI Service")

    await cache_service.close()
    await db_manager.close()

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        description="High-performance REST API for AI/ML backend services",
        version=settings.APP_VERSION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOC_URL,
        openapi_url=settings.OPENAPI_URL,
        lifespan=lifespan,
    )

    # Setup logging
    setup_logging()

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

    # Custom middlewares (order matters - last added = first executed)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MonitoringMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )

    # Include API router
    app.include_router(api_router)

    # Metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # Health check
    @app.get("/health", include_in_schema=False)
    async def health_check(request: Request):
        """Health check endpoint with dependency checks."""
        from datetime import datetime, timezone

        checks = {}
        overall_status = "healthy"

        # Database check
        try:
            async with db_manager.session() as session:
                await session.execute("SELECT 1")
            checks["database"] = "healthy"
        except Exception as e:
            checks["database"] = f"unhealthy: {str(e)}"
            overall_status = "degraded"

        # Cache check
        try:
            await cache_service.ping()
            checks["cache"] = "healthy"
        except Exception as e:
            checks["cache"] = f"unhealthy: {str(e)}"
            overall_status = "degraded"

        # Storage check
        try:
            await storage_service.backend.ping() if hasattr(storage_service.backend, 'ping') else True
            checks["storage"] = "healthy"
        except Exception:
            checks["storage"] = "unknown"

        return JSONResponse(
            status_code=200 if overall_status == "healthy" else 503,
            content={
                "status": overall_status,
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": checks,
            },
        )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger = get_logger("app.error")
        logger.exception(
            "Unhandled exception",
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                },
                "request_id": request_id,
            },
        )

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS if not settings.DEBUG else 1,
        log_level=settings.LOG_LEVEL.lower(),
    )