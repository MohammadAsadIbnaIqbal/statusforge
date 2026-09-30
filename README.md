# StatusForge

A lightweight public status-page and incident communication platform for small SaaS products and teams.

StatusForge provides a clear, professional way to communicate system status, outages, and maintenance without the overhead of enterprise incident management platforms.

## Core Capabilities

- **Public Status Page**: A clean, accessible, mobile-responsive public view for your users.
- **Service Management**: Define and manage the components of your system.
- **Incident Lifecycle**: Create, investigate, identify, monitor, and resolve incidents.
- **Incident Updates**: Post chronological updates to active incidents.
- **Resolved History**: Keep a public log of past incidents for transparency.
- **Email Subscriptions**: Allow users to subscribe to updates with email confirmation.
- **Background Notifications**: Send email notifications asynchronously without blocking API responses.
- **High-Performance Caching**: Fast public page rendering with Redis.

### Explicit Non-Goals

StatusForge is **not**:
- Uptime monitoring or automated pinging
- PagerDuty or an on-call rotation manager
- Log aggregation or APM
- A support or ticketing system
- Multi-tenant enterprise infrastructure
- A full replacement for Better Stack or Atlassian Statuspage

## Architecture

```text
Frontend (Vercel / Next.js)
      │
      ▼
FastAPI Backend (Render Web Service) ──▶ Supabase PostgreSQL (Primary Data)
      │
      ▼
   Embedded ARQ Worker ──▶ Email Provider (Resend)
      │
      ▼
 Render Key Value (Redis)
```

## Local Development Setup

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.10+ (for running tests outside Docker)

### 1. Start the Backend Infrastructure

```bash
# Clone the repository
git clone https://github.com/MohammadAsadIbnaIqbal/statusforge.git
cd statusforge

# Start PostgreSQL, Redis, FastAPI, and ARQ worker
docker-compose up --build -d
```

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API Docs: http://localhost:8000/docs

## Environment Configuration

Copy the example configuration files and adjust if necessary:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

### Backend Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | A strong random string for JWT signing. |
| `DATABASE_URL` | PostgreSQL connection string. |
| `REDIS_URL` | Redis connection string. |
| `ALLOWED_ORIGINS` | CORS origins (e.g. `http://localhost:3000`). |
| `APP_URL` | The base URL of the backend API. |
| `NOTIFICATION_MODE` | `log` (default) or `live`. |
| `EMAIL_PROVIDER_API_KEY` | Resend API Key (required for `live` mode). |
| `EMAIL_SENDER` | The "From" email address. |

## Notifications

StatusForge supports two notification modes, controlled by `NOTIFICATION_MODE`:

1. **`log` (Default)**: Emulates sending emails by logging the payload and recipient to the console. Perfect for local development.
2. **`live`**: Sends real emails via Resend. Requires `EMAIL_PROVIDER_API_KEY` to be configured.

## Testing

**Backend** (Requires a running local database and Redis):
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest tests
```

**Frontend**:
```bash
cd frontend
npm run test
```

## Deployment Guidance

StatusForge is designed to be fully deployable on free-tier infrastructure for small portfolio projects and teams.

**Important:** This is a lightweight monolithic deployment architecture. It does not claim high availability, guaranteed delivery, zero-downtime deployment, or enterprise-scale distributed worker infrastructure. The embedded background worker is highly cost-effective but is not equivalent to a dedicated fault-tolerant worker service.

- **Frontend**: Deploy to **Vercel**. Set the root directory to `frontend`. Ensure `NEXT_PUBLIC_API_URL` points to your backend production URL.
- **Backend**: Deploy as a single **Render Web Service** (Docker environment). Set the root directory to `backend`. StatusForge uses an **embedded ARQ worker** running inside the FastAPI process, meaning you do **not** need to deploy or pay for a separate Render Background Worker.
- **Database**: Use **Supabase** PostgreSQL. StatusForge uses Alembic migrations; Render will automatically run the existing migration command defined in the backend container startup.
- **Redis**: Use **Render Key Value** (Redis) in the same Singapore region as your Render Web Service. Provide the internal `REDIS_URL` to your backend.
- **Email**: Use **Resend**. For initial deployment, keep `NOTIFICATION_MODE=log`. Switch to `live` and provide `EMAIL_PROVIDER_API_KEY` when ready to send real emails.
- **Monitoring**: Sentry is optional and can be configured by supplying a `SENTRY_DSN`.

*Note: Local development via Docker Compose will still spin up a separate worker container for ease of debugging, but production uses the embedded worker strategy.*
