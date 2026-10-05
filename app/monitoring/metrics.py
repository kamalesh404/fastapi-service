"""
Prometheus metrics for monitoring.

Provides standard metrics for HTTP requests, database, and custom business metrics.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from prometheus_client.core import CollectorRegistry
from starlette.responses import Response

from app.core.config import settings

# Create custom registry
registry = CollectorRegistry()

# Application info
app_info = Info(
    "fastapi_service_info",
    "Application information",
    registry=registry,
)
app_info.info({
    "version": "1.0.0",
    "environment": settings.ENVIRONMENT,
})

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry,
)

http_request_size = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    registry=registry,
)

http_response_size = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    registry=registry,
)

# Database metrics
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry,
)

db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
    registry=registry,
)

db_connections_idle = Gauge(
    "db_connections_idle",
    "Idle database connections",
    registry=registry,
)

# Redis metrics
redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "result"],
    registry=registry,
)

redis_connection_errors = Counter(
    "redis_connection_errors_total",
    "Redis connection errors",
    registry=registry,
)

# Celery metrics
celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],
    registry=registry,
)

celery_task_duration = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0),
    registry=registry,
)

# Business metrics
users_registered = Counter(
    "users_registered_total",
    "Total registered users",
    ["source"],
    registry=registry,
)

users_active = Gauge(
    "users_active",
    "Currently active users",
    registry=registry,
)

items_created = Counter(
    "items_created_total",
    "Total items created",
    ["category"],
    registry=registry,
)

api_errors_total = Counter(
    "api_errors_total",
    "Total API errors",
    ["endpoint", "error_type"],
    registry=registry,
)

# Authentication metrics
auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["method", "result"],
    registry=registry,
)

# File storage metrics
storage_uploads_total = Counter(
    "storage_uploads_total",
    "Total file uploads",
    ["storage_type", "result"],
    registry=registry,
)

storage_downloads_total = Counter(
    "storage_downloads_total",
    "Total file downloads",
    ["storage_type"],
    registry=registry,
)


def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(registry),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def record_http_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
    request_size: int = 0,
    response_size: int = 0,
) -> None:
    """Record HTTP request metrics."""
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=status_code,
    ).inc()

    http_request_duration.labels(
        method=method,
        endpoint=endpoint,
    ).observe(duration)

    if request_size > 0:
        http_request_size.labels(
            method=method,
            endpoint=endpoint,
        ).observe(request_size)

    if response_size > 0:
        http_response_size.labels(
            method=method,
            endpoint=endpoint,
        ).observe(response_size)


def record_db_query(operation: str, table: str, duration: float) -> None:
    """Record database query metrics."""
    db_query_duration.labels(
        operation=operation,
        table=table,
    ).observe(duration)


def record_auth_attempt(method: str, success: bool) -> None:
    """Record authentication attempt."""
    auth_attempts_total.labels(
        method=method,
        result="success" if success else "failure",
    ).inc()


def record_api_error(endpoint: str, error_type: str) -> None:
    """Record API error."""
    api_errors_total.labels(
        endpoint=endpoint,
        error_type=error_type,
    ).inc()


def record_user_registration(source: str = "email") -> None:
    """Record user registration."""
    users_registered.labels(source=source).inc()


def record_item_creation(category: Optional[str] = None) -> None:
    """Record item creation."""
    items_created.labels(category=category or "unknown").inc()


def record_storage_upload(storage_type: str, success: bool) -> None:
    """Record file upload."""
    storage_uploads_total.labels(
        storage_type=storage_type,
        result="success" if success else "failure",
    ).inc()


def record_storage_download(storage_type: str) -> None:
    """Record file download."""
    storage_downloads_total.labels(storage_type=storage_type).inc()


def record_celery_task(task_name: str, duration: float, success: bool) -> None:
    """Record Celery task metrics."""
    celery_tasks_total.labels(
        task_name=task_name,
        status="success" if success else "failure",
    ).inc()
    celery_task_duration.labels(task_name=task_name).observe(duration)


def update_active_users(count: int) -> None:
    """Update active users gauge."""
    users_active.set(count)


def update_db_connections(active: int, idle: int) -> None:
    """Update database connection gauges."""
    db_connections_active.set(active)
    db_connections_idle.set(idle)