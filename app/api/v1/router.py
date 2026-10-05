"""
API v1 router.

Combines all v1 endpoints into a single router.
"""

from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.users.router import router as users_router
from app.api.v1.items.router import router as items_router

# Main v1 router
api_v1_router = APIRouter(prefix="/api/v1")

# Include all v1 routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(items_router)

# Export for main app
__all__ = ["api_v1_router"]