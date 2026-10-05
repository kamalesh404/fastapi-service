# System Architecture

## Overview

FastAPI Service is a production-ready REST API built with modern Python async patterns, designed for AI/ML backend services.

## High-Level Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  Nginx/     │────▶│  FastAPI    │
│  (Web/Mob)  │     │  Load Bal.  │     │  Application│
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
        ┌─────────────┐     ┌─────────────┐    │
        │  Prometheus │◀───│  Metrics    │    │
        │  Grafana    │    │  Endpoint   │    │
        └─────────────┘     └─────────────┘    │
                                               │
        ┌─────────────┐     ┌─────────────┐    │
        │ PostgreSQL  │◀───│  SQLAlchemy │◀───┘
        │  (Async)    │    │  2.0 ORM    │
        └─────────────┘     └─────────────┘
                                               │
        ┌─────────────┐     ┌─────────────┐    │
        │   Redis     │◀───│  Cache/     │◀───┘
        │  (Cache/    │    │  Queue/     │
        │   Celery)   │    │  PubSub     │
        └─────────────┘     └─────────────┘
```

## Core Components

### 1. API Layer (`app/api/`)
- **Versioned endpoints**: `/api/v1/`, `/api/v2/`
- **RESTful design** with proper HTTP semantics
- **OpenAPI 3.0** auto-generation
- **Request validation** via Pydantic schemas

### 2. Core (`app/core/`)
- **Configuration**: Pydantic Settings with env support
- **Security**: JWT tokens, password hashing, OAuth2
- **Dependencies**: FastAPI dependency injection

### 3. Database (`app/db/`, `app/models/`)
- **Async SQLAlchemy 2.0** with connection pooling
- **Declarative models** with type hints
- **Alembic migrations** for schema evolution
- **Soft delete** pattern for data safety

### 4. Services (`app/services/`)
- **CacheService**: Redis with auto-serialization
- **StorageService**: Multi-backend (Local/S3/MinIO)
- **CeleryService**: Async task processing

### 5. Monitoring (`app/monitoring/`)
- **Metrics**: Prometheus counters, histograms, gauges
- **Logging**: Structured JSON with correlation IDs
- **Health**: Dependency checks (DB, Cache, Storage)

### 5. Middleware (`app/middleware/`)
- **Monitoring**: Request/response metrics
- **Rate Limiting**: Redis sliding window
- **Security**: CSP, HSTS, XSS protection
- **Correlation IDs**: Request tracing

## Data Flow

### Authentication Flow
```
1. Client → POST /api/v1/auth/login (credentials)
2. Server → Validate → Create JWT pair
3. Server → Store refresh token hash in DB
4. Server → Return access_token + refresh_token (cookie)
5. Client → Use access_token in Authorization header
6. Server → Validate JWT → Get user from DB
7. Token expired → POST /auth/refresh (cookie)
8. Server → Rotate tokens → Return new pair
```

### Request Processing
```
Request → Middleware Stack → Route Handler → Service → DB/Cache
                     ↓
              Correlation ID
              Metrics
              Logging
              Rate Limit
              Security Headers
```

### Async Task Processing
```
API Endpoint → Celery Task → Redis Queue → Worker → Result Backend
                    ↓
              Monitoring
              Retry Logic
              Error Handling
```

## Security Architecture

### Authentication
- **JWT Access Tokens**: 15 min expiry, RS256/HS256
- **Refresh Tokens**: 7 days, rotation, revocation
- **Password Hashing**: Bcrypt (cost factor 12)
- **Scope-based Authorization**: read, write, admin

### Transport Security
- **HTTPS only** in production
- **HSTS** with preload
- **Secure cookies** (HttpOnly, SameSite=Lax)
- **CORS** configured per environment

### Input Validation
- **Pydantic schemas** for all requests
- **SQL injection prevention**: SQLAlchemy ORM
- **XSS prevention**: Content-Type validation
- **Rate limiting**: Per-IP/User configurable

## Deployment Architecture

### Production
```
                    ┌─────────────────┐
                    │   Nginx/ALB     │
                    │  (SSL Term.)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │ App 1   │    │ App 2   │    │ App N   │
        │ (uvicorn)    │ (uvicorn)    │ (uvicorn)    │
        └────┬────┘    └────┬────┘    └────┬────┘
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                   ┌─────────────────┐
                   │  PostgreSQL     │
                   │  (Primary/Replica)│
                   └─────────────────┘
                            ▼
                   ┌─────────────────┐
                   │  Redis Cluster  │
                   │  (Cache/Queue)  │
                   └─────────────────┘
```

### Container Strategy
- **Multi-stage Dockerfile** (base → deps → build → prod)
- **Non-root user** (appuser)
- **Health checks** at container & app level
- **Resource limits** (CPU/Memory)

## Scaling Considerations

### Horizontal Scaling
- **Stateless app pods** - scale behind load balancer
- **Session affinity** not required (JWT stateless)
- **Database**: Read replicas for read-heavy workloads
- **Redis**: Cluster mode for high throughput

### Performance Optimization
- **Connection pooling** (DB: 20, Redis: 50)
- **Async I/O** throughout (no blocking calls)
- **Caching strategy**: Cache-Aside with TTL
- **Pagination**: Cursor-based for large datasets

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Language | Python | 3.12+ |
| Framework | FastAPI | 0.111+ |
| Database | PostgreSQL | 16+ |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | 1.13+ |
| Cache/Queue | Redis | 7+ |
| Async Tasks | Celery | 5.4+ |
| Monitoring | Prometheus/Grafana | Latest |
| Container | Docker | 24+ |
| Orchestration | Docker Compose / K8s | - |

## Future Extensibility

- **GraphQL endpoint** (v2 API)
- **WebSocket support** for real-time features
- **gRPC** for service-to-service communication
- **Event sourcing** for audit trails
- **Multi-tenancy** for SaaS deployment