# CLAUDE.md - Instructions for Claude AI

## Project Context

This is a **production-ready FastAPI service** for AI/ML backend services. Built with Python 3.12+, FastAPI, PostgreSQL, Redis, and Celery.

## Code Style Rules

### Python
- **Type hints mandatory** on all function signatures
- **Async/await** for all I/O operations
- **Pydantic v2** for validation (use `model_config = ConfigDict()`)
- **SQLAlchemy 2.0** async patterns
- **Max 100 chars** per line
- **Double quotes** for strings
- **No `Any` types** unless absolutely necessary

### Imports
```python
# Standard library first
import asyncio
from datetime import datetime, timezone
from typing import Optional, List

# Third party
from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Local
from app.core.config import settings
from app.db.session import get_db
```

### Error Handling
```python
# Use specific HTTP exceptions
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="User not found",
)
```

### Database Patterns
```python
# Always use async session with context manager
async with db_manager.session() as session:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
```

## Project-Specific Patterns

### Configuration
```python
# Use Settings class from app.core.config
from app.core.config import settings

# Access: settings.DATABASE_URL, settings.SECRET_KEY, etc.
```

### Security
- **JWT tokens**: Use `app.core.security` functions
- **Password hashing**: `get_password_hash()`, `verify_password()`
- **Dependencies**: Use `get_current_user`, `require_scopes()`

### Monitoring
- **Metrics**: Use `app.monitoring.metrics` functions
- **Logging**: Use `app.monitoring.logging.get_logger()`

## Common Tasks

### Adding New API Endpoint
1. Create schema in `app/schemas/__init__.py`
2. Add route in `app/api/v1/{resource}/router.py`
3. Include router in `app/api/v1/router.py`
4. Add tests in `tests/`

### Adding Database Model
1. Create model in `app/models/{name}.py`
2. Export in `app/models/__init__.py`
3. Create Alembic migration: `alembic revision --autogenerate -m "add model"`
4. Run migration: `alembic upgrade head`

### Adding Background Task
1. Add task in `app/services/celery.py`
2. Use `@celery_app.task(bind=True, base=BaseTask)`
4. Call via `celery_app.send_task()` or `.delay()`

## Testing

### Run Tests
```bash
pytest -v --cov=app --cov-report=term-missing
```

### Test Patterns
```python
# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_user_creation(db_session):
    user = User(email="test@example.com", ...)
    db_session.add(user)
    await db_session.commit()
    assert user.id is not None
```

## File Organization

```
app/
├── api/           # HTTP routes
├── core/          # Config, security
├── db/            # Database session
├── middleware/    # Custom middleware
├── models/        # SQLAlchemy models
├── monitoring/    # Metrics, logging
├── schemas/       # Pydantic schemas
├── services/      # Business logic
├── main.py        # Entry point
```

## Commands

```bash
# Development
uvicorn app.main:app --reload

# Testing
pytest -v --cov=app

# Linting
ruff check app/ && mypy app/

# Formatting
black app/ && ruff check --fix app/

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Docker
docker compose up -d
docker compose logs -f app
```

## Red Flags (Don't Do)

- ❌ Synchronous DB calls in async functions
- ❌ Raw SQL strings (use ORM)
- ❌ Hardcoded secrets (use settings)
- ❌ Missing type hints
- ❌ Blocking I/O in async context
- ❌ Global mutable state
- ❌ Catching bare `Exception`
- ❌ Print statements (use structured logging)

## Quick Reference

| Need | Location |
|------|----------|
| Config | `app/core/config.py` |
| Auth | `app/core/security.py` |
| DB Session | `app/db/session.py` |
| Models | `app/models/` |
| Schemas | `app/schemas/__init__.py` |
| API Routes | `app/api/v1/` |
| Services | `app/services/` |
| Metrics | `app/monitoring/metrics.py` |
| Logging | `app.monitoring.logging` |
| Middleware | `app/middleware/` |
| Celery Tasks | `app/services/celery.py` |