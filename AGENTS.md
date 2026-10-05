# AI Agents Guide

Instructions for AI agents working on this codebase.

## Project Overview

**FastAPI Service** - Production-ready REST API for AI/ML backend services.

- **Language**: Python 3.12+
- **Framework**: FastAPI 0.111+
- **Database**: PostgreSQL (async SQLAlchemy 2.0)
- **Cache/Queue**: Redis + Celery
- **Auth**: JWT with refresh token rotation

## Code Style & Standards

### Python
- Use **type hints** everywhere
- Follow **PEP 8** (enforced by Ruff)
- Max line length: **100 chars**
- Use **async/await** for I/O operations
- Prefer **composition over inheritance**

### Git Commits
Follow **Conventional Commits**:
```
feat: add user authentication
fix: resolve token refresh bug
docs: update API documentation
refactor: simplify user service
test: add integration tests for auth
```

### Branch Naming
```
feature/user-authentication
fix/token-refresh-issue
docs/api-documentation
refactor/user-service
```

## Development Workflow

1. **Create feature branch** from `main`
2. **Write tests first** (TDD preferred)
3. **Implement feature** with type hints
4. **Run quality checks**:
   ```bash
   ruff check app/
   mypy app/
   black --check app/
   pytest --cov=app
   ```
5. **Create PR** with clear description
6. **Request review** from maintainers

## Project Structure

```
app/
├── api/              # API routes (v1, v2)
│   ├── v1/          # Stable API
│   └── v2/          # Development API
├── core/             # Core configuration & security
├── db/               # Database session management
├── middleware/       # Custom middleware
├── models/           # SQLAlchemy models
├── monitoring/       # Metrics & logging
├── schemas/          # Pydantic schemas
├── services/         # Business logic services
├── main.py           # Application entry point
```

## Key Patterns

### Dependency Injection
```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    ...
```

### Error Handling
```python
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="User not found",
)
```

### Database Operations
```python
async with db_manager.session() as session:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
```

## Testing Guidelines

- **Unit tests**: Test individual functions/classes
- **Integration tests**: Test API endpoints with real DB
- **Fixtures**: Use `tests/conftest.py` for shared fixtures
- **Coverage**: Aim for **≥80%** overall, **≥90%** for critical paths

## Security Requirements

- **Never commit secrets** (use `.env` files)
- **Validate all inputs** with Pydantic schemas
- **Use parameterized queries** (SQLAlchemy ORM)
- **Implement rate limiting** on all endpoints
- **Log security events** (failed logins, token reuse)

## Documentation

- Update **README.md** for user-facing changes
- Update **API docs** (auto-generated from OpenAPI)
- Update **ARCHITECTURE.md** for structural changes
- Add **docstrings** to all public functions/classes

## Useful Commands

```bash
# Run development server
uvicorn app.main:app --reload

# Run tests
pytest -v --cov=app

# Run linting
ruff check app/ && mypy app/

# Format code
black app/ && ruff check --fix app/

# Generate migration
alembic revision --autogenerate -m "description"

# Run migration
alembic upgrade head
```

## Getting Help

- Check **README.md** for setup instructions
- Check **ARCHITECTURE.md** for system design
- Review existing code for patterns
- Open an issue for questions