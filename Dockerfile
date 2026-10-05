# FastAPI Service - Production Dockerfile
# Multi-stage build for minimal production image

# =============================================================================
# Base Stage
# =============================================================================
FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# =============================================================================
# Dependencies Stage
# =============================================================================
FROM base AS deps

# Copy dependency files
COPY pyproject.toml requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Build Stage
# =============================================================================
FROM deps AS build

# Copy application code
COPY app/ ./app/

# Run tests (if any)
# RUN pytest --cov=app --cov-fail-under=80

# =============================================================================
# Production Stage
# =============================================================================
FROM base AS production

# Copy installed dependencies
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=build /app/app ./app

# Create storage directory
RUN mkdir -p /app/storage && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# =============================================================================
# Development Stage
# =============================================================================
FROM deps AS development

# Install dev dependencies
RUN pip install --no-cache-dir -r requirements-dev.txt 2>/dev/null || true

# Install debug tools
RUN pip install --no-cache-dir debugpy ipdb

# Copy application code
COPY app/ ./app/

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]