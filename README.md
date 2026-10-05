# FastAPI Service

[![CI](https://github.com/kamalesh404/fastapi-service/workflows/CI/badge.svg)](https://github.com/kamalesh404/fastapi-service/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg)](https://fastapi.tiangolo.com/)

> **Production-ready FastAPI service** for AI/ML backend services with complete authentication, monitoring, and deployment infrastructure.

## ✨ Features

- **🔐 Complete Authentication**: JWT access/refresh tokens with rotation, bcrypt hashing, RBAC (USER/MODERATOR/ADMIN/SUPERADMIN), OAuth2 ready
- **🗄️ Database**: Async PostgreSQL with SQLAlchemy 2.0, Alembic migrations, soft deletes, tagging
- **⚡ Caching & Queue**: Redis with auto-serialization, Celery async tasks with Beat scheduler
- **📁 File Storage**: Multi-backend (Local/S3/MinIO) with presigned URLs
- **📊 Monitoring**: Prometheus metrics, structured JSON logging, health checks
- **🛡️ Security**: Rate limiting, CSP/HSTS headers, secure cookies, input validation
- **🐳 DevOps Ready**: Docker multi-stage, docker-compose, GitHub Actions CI/CD
- **📚 Documentation**: Auto-generated OpenAPI/Swagger, comprehensive docs

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose (recommended)

### Development Setup

```bash
# Clone repository
git clone https://github.com/kamalesh404/fastapi-service.git
cd fastapi-service

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Start with Docker Compose (recommended)
docker compose up -d

# Or run locally
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Access Points
- **API**: http://localhost:8000
- **Docs (Swagger)**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 📖 Documentation

- [Architecture](ARCHITECTURE.md) - System design and data flows
- [Contributing](CONTRIBUTING.md) - Development guidelines
- [Agent Guide](AGENTS.md) - Instructions for AI agents
- [API Docs](http://localhost:8000/api/docs) - Interactive OpenAPI docs

## 🏗️ Project Structure

```
fastapi-service/
├── app/
│   ├── api/           # API routes (v1, v2)
│   ├── core/          # Config, security
│   ├── db/            # Database session
│   ├── middleware/    # Custom middleware
│   ├── models/        # SQLAlchemy models
│   ├── monitoring/    # Metrics & logging
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   └── main.py        # Entry point
├── tests/             # Test suite
├── migrations/        # Alembic migrations
├── .github/workflows/ # CI/CD pipelines
├── monitoring/        # Prometheus/Grafana configs
├── Dockerfile         # Multi-stage build
├── docker-compose.yml # Full stack
├── pyproject.toml     # Project config
└── requirements.txt   # Dependencies
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | **Required** |
| `DEBUG` | Debug mode | `false` |
| `ENVIRONMENT` | `development\|staging\|production` | `development` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:3000` |
| `STORAGE_TYPE` | `local\|s3\|minio` | `local` |

See [.env.example](.env.example) for all options.

## 🧪 Testing

```bash
# Run all tests with coverage
pytest -v --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_auth.py -v

# Run with Docker
docker compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit
```

## 🐳 Docker

### Production
```bash
docker compose up -d
```

### Development
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### With Monitoring
```bash
docker compose --profile monitoring up -d
```

### With S3/MinIO Storage
```bash
docker compose --profile storage up -d
```

## 🔄 CI/CD Pipeline

GitHub Actions workflow includes:
- **Lint**: Ruff, MyPy, Black
- **Test**: Unit + Integration with PostgreSQL/Redis
- **Security**: Bandit, Safety, pip-audit
- **Build**: Multi-stage Docker image to GHCR
- **Deploy**: Staging (develop) → Production (main)

## 📦 API Endpoints

### Authentication
```
POST   /api/v1/auth/register          # Register new user
POST   /api/v1/auth/login             # Login (returns tokens)
POST   /api/v1/auth/refresh           # Refresh access token
POST   /api/v1/auth/logout            # Logout (revokes token)
POST   /api/v1/auth/forgot-password   # Request password reset
POST   /api/v1/auth/reset-password    # Reset password
POST   /api/v1/auth/verify-email      # Verify email
GET    /api/v1/auth/me                # Current user profile
```

### Users (Admin)
```
GET    /api/v1/users                  # List users (paginated)
GET    /api/v1/users/me               # Current user profile
PATCH  /api/v1/users/me               # Update profile
GET    /api/v1/users/{id}             # Get user (admin)
PATCH  /api/v1/users/{id}             # Update user (admin)
DELETE /api/v1/users/{id}             # Delete user (superadmin)
POST   /api/v1/users/{id}/activate    # Activate user (admin)
POST   /api/v1/users/{id}/suspend     # Suspend user (admin)
POST   /api/v1/users/{id}/role        # Change role (superadmin)
```

### Items
```
POST   /api/v1/items                  # Create item
GET    /api/v1/items                  # List items (paginated)
GET    /api/v1/items/my-items         # My items
GET    /api/v1/items/{id}             # Get item
PATCH  /api/v1/items/{id}             # Update item
DELETE /api/v1/items/{id}             # Soft delete item
POST   /api/v1/items/{id}/restore     # Restore item
GET    /api/v1/items/public           # Public items (no auth)
GET    /api/v1/items/categories/list  # List categories
GET    /api/v1/items/tags/list        # List tags
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Ensure all checks pass (`ruff`, `mypy`, `pytest`)
5. Commit with conventional commits
6. Push and open Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**kamalesh404**
- GitHub: [@kamalesh404](https://github.com/kamalesh404)
- Email: kamalesh404@users.noreply.github.com

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit
- [Pydantic](https://pydantic.dev/) - Data validation
- [Celery](https://docs.celeryq.dev/) - Distributed task queue
- [Prometheus](https://prometheus.io/) - Monitoring & alerting