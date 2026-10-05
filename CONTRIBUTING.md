# Contributing Guide

Thank you for your interest in contributing! This guide will help you get started.

## 🤝 Ways to Contribute

- 🐛 **Bug Reports**: Found a bug? Open an issue with details
- 💡 **Feature Requests**: Have an idea? We'd love to hear it
- 📝 **Documentation**: Improve docs, fix typos, add examples
- 🧪 **Tests**: Add tests, improve coverage
- 🔧 **Code**: Fix bugs, add features, refactor

## 🚀 Getting Started

### 1. Fork & Clone
```bash
git clone https://github.com/your-username/fastapi-service.git
cd fastapi-service
```

### 2. Set Up Development Environment
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env
# Edit .env with your local settings
```

### 3. Start Services
```bash
# Using Docker (recommended)
docker compose up -d postgres redis

# Or start locally
# Ensure PostgreSQL and Redis are running
```

### 4. Run Migrations
```bash
alembic upgrade head
```

### 5. Verify Setup
```bash
# Run tests
pytest -v

# Start development server
uvicorn app.main:app --reload

# Visit http://localhost:8000/api/docs
```

## 📝 Development Workflow

### Branching Strategy
```
main ← develop ← feature/your-feature-name
```

### Commit Convention
Follow [Conventional Commits](https://www.conventionalcommits.org/):

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `refactor` | Code restructuring |
| `test` | Adding tests |
| `chore` | Maintenance |
| `perf` | Performance improvement |

**Examples:**
```
feat: add user email verification
fix: resolve token refresh race condition
docs: update API documentation for v2
refactor: simplify user service layer
test: add integration tests for auth
```

### Pull Request Process

1. **Create feature branch** from `develop`
2. **Write tests** for new functionality
2. **Implement changes** with type hints
3. **Run quality checks**:
   ```bash
   ruff check app/
   mypy app/
   black --check app/
   pytest --cov=app --cov-fail-under=80
   ```
4. **Update documentation** if needed
5. **Push & create PR** against `develop`
6. **Request review** from maintainers

### PR Requirements
- ✅ All CI checks pass
- ✅ Code coverage ≥ 80% (90% for critical paths)
- ✅ No linting/type errors
- ✅ Tests added for new features
- ✅ Documentation updated
- ✅ Conventional commit messages

## 🧪 Testing Guidelines

### Test Structure
```
tests/
├── conftest.py          # Shared fixtures
├── test_auth.py         # Auth tests
├── test_users.py        # User tests
├── test_items.py        # Item tests
└── test_integration.py  # Full API tests
```

### Writing Tests
```python
# Use pytest-asyncio for async tests
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_user_registration(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepass123",
        "password_confirm": "securepass123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
```

### Test Fixtures (conftest.py)
```python
@pytest.fixture
async def db_session():
    async with db_manager.session() as session:
        yield session

@pytest.fixture
async def client(db_session):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

## 🎨 Code Style

### Python Standards
- **PEP 8** enforced by **Ruff**
- **Type hints** on all functions
- **Max line length**: 100 characters
- **Double quotes** for strings
- **No `Any` types** unless necessary

### Tools Configuration
```bash
# Linting
ruff check app/

# Type checking
mypy app/

# Formatting
black app/
ruff check --fix app/

# All checks
ruff check app/ && mypy app/ && black --check app/
```

### Pre-commit Hooks (Optional)
```bash
pip install pre-commit
pre-commit install
```

## 🔒 Security Guidelines

### Reporting Vulnerabilities
**DO NOT** open public issues for security vulnerabilities.
Email: security@kamalesh404.local

### Secure Coding
- Never commit secrets (use `.env`)
- Validate all inputs with Pydantic
- Use parameterized queries (SQLAlchemy ORM)
- Implement rate limiting
- Log security events (failed logins, token reuse)

## 📚 Documentation Standards

### Code Documentation
```python
async def create_user(
    email: str,
    username: str,
    password: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Create a new user account.

    Args:
        email: User's email address
        username: Unique username
        password: Plain text password (will be hashed)
        db: Database session

    Returns:
        Created User object

    Raises:
        HTTPException: If email/username already exists
    """
```

### API Documentation
- Auto-generated from Pydantic schemas
- Update docstrings for endpoint changes
- Add examples for complex endpoints

## 🏷️ Release Process

### Versioning
[Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

| Change | Version Bump |
|--------|-------------|
| Breaking API change | MAJOR |
| New feature (backward compatible) | MINOR |
| Bug fix | PATCH |

### Release Checklist
- [ ] All CI checks pass
- [ ] Version bumped in `pyproject.toml`
- [ ] `CHANGELOG.md` updated
- [ ] Tests pass locally
- [ ] Tag created: `git tag v1.2.3`
- [ ] GitHub Release created
- [ ] Docker image pushed

## 🏷️ Issue & PR Labels

| Label | Description |
|-------|-------------|
| `bug` | Something isn't working |
| `enhancement` | New feature or improvement |
| `documentation` | Docs improvements |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention needed |
| `priority: high/medium/low` | Urgency |
| `status: needs-triage/in-progress/blocked` | Status |

## 📞 Getting Help

- **Discord**: [Join our community](https://discord.gg/example)
- **Discussions**: [GitHub Discussions](https://github.com/kamalesh404/fastapi-service/discussions)
- **Email**: support@kamalesh404.local

## 📜 Code of Conduct

### Our Pledge
We pledge to make participation harassment-free for everyone.

### Standards
- Be respectful and inclusive
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy

### Enforcement
Violations may result in temporary or permanent bans.

---

**Thank you for contributing!** 🎉