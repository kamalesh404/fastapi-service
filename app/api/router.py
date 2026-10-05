"""
Main API router.

Combines all API versions into a single router.
"""

from fastapi import APIRouter

from app.api.v1.router import api_v1_router
from app.api.v2.router import api_v2_router

# Main API router
api_router = APIRouter()

# Include all versions
api_router.include_router(api_v1_router)
api_router.include_router(api_v2_router)

# Health check at root level
@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.core.config import settings
    from datetime import datetime, timezone

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@api_router.get("/")
async def root():
    """Root endpoint with API information."""
    from app.core.config import settings

    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": settings.DOCS_URL,
        "api_versions": {
            "v1": "/api/v1",
            "v2": "/api/v2 (development)",
        },
    }

__all__ = ["api_router"]