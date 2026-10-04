"""FastAPI application main entry point."""

from fastapi import FastAPI
from .routers import auth, items, upload
from .models import Base
from .db import engine

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="FastAPI Service",
    description="High-performance REST API for AI/ML backend services",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Include routers
app.include_router(auth.router, prefix=f"{API_V1_STR}/auth", tags=["authentication"])
app.include_router(items.router, prefix=f"{API_V1_STR}/items", tags=["items"])
app.include_router(upload.router, prefix=f"{API_V1_STR}/upload", tags=["upload"])

# Health check endpoint
@app.get("/health", tags=["root"])
async def health_check():
    return {"status": "healthy", "message": "FastAPI service is running"}

# Root endpoint
@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to FastAPI Service",
        "docs": "/api/docs",
        "version": "1.0.0"
    }