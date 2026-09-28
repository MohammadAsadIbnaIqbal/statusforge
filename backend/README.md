# StatusForge Backend

A high-performance, production-ready asynchronous Python REST API built with FastAPI, SQLModel, Alembic, PostgreSQL, Redis, and ARQ—fully containerized with Docker.

This is the backend for StatusForge, an open-source status page and incident communication platform.

## 🌟 Key Features
* **Asynchronous ORM**: High-performance async database operations using `SQLModel` and `asyncpg`.
* **In-Memory Caching**: Ultra-fast response caching using `Redis` and `fastapi-cache2` to reduce database load.
* **Background Task Queue**: Asynchronous job processing for email delivery and background tasks using `ARQ` and Redis.
* **Observability & Error Tracking**: Real-time error reporting and performance tracing integrated with `Sentry`.
* **Database Migrations**: Schema version management handled automatically with `Alembic`.
* **Security & Auth**: Argon2id password hashing and OAuth2 Bearer JWT authentication.
* **Rate Limiting**: Protection against brute-force attacks on sensitive endpoints via `slowapi`.
* **Containerization**: Dockerized multi-stage builds running seamlessly in production.
* **CI/CD Pipeline**: Automated unit/integration test execution via GitHub Actions on every pull request.

## 🛠️ Tech Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Database**: PostgreSQL (Supabase)
- **Caching & Broker**: Redis
- **Async Queue**: ARQ
- **Monitoring**: Sentry
- **ORM & Migrations**: SQLModel / Alembic
- **Containerization**: Docker & Docker Compose
- **Hosting**: Render
