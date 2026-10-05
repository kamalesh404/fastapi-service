"""
API v2 router.

Future API version with enhanced features.
Placeholder for API versioning demonstration.
"""

from fastapi import APIRouter

api_v2_router = APIRouter(prefix="/api/v2")

# v2 endpoints will be added here
# Example: Enhanced search, GraphQL, etc.

@api_v2_router.get("/info")
async def v2_info():
    """API v2 information."""
    return {
        "version": "2.0.0",
        "status": "development",
        "message": "API v2 is under development",
        "features": [
            "Enhanced search",
            "GraphQL support",
            "Real-time subscriptions",
            "Advanced analytics",
        ],
    }

__all__ = ["api_v2_router"]