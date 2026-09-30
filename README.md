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

\\\
Frontend (Next.js) 
      ¦
      ?
FastAPI Backend --? PostgreSQL (Primary Data Store)
      ¦
      ?
    Redis
      ¦
      ?
ARQ Background Worker --? Email Provider (Resend)
\\\

## Local Development Setup

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.10+ (for running tests outside Docker)

### 1. Start the Backend Infrastructure

\\\ash
# Clone the repository
git clone https://github.com/yourusername/statusforge.git
cd statusforge

# Start PostgreSQL, Redis, FastAPI, and ARQ worker
docker-compose up --build -d
\\\

### 2. Start the Frontend

\\\ash
cd frontend
npm install
npm run dev
\\\
The application will be available at:
- Frontend: http://localhost:3000
- Backend API Docs: http://localhost:8000/docs

## Environment Configuration

Copy the example configuration files and adjust if necessary:
\\\ash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
\\\

### Backend Environment Variables
| Variable | Description |
|----------|-------------|
| \SECRET_KEY\ | A strong random string for JWT signing. |
| \DATABASE_URL\ | PostgreSQL connection string. |
| \REDIS_URL\ | Redis connection string. |
| \ALLOWED_ORIGINS\ | CORS origins (e.g. \http://localhost:3000\). |
| \APP_URL\ | The base URL of the backend API. |
| \NOTIFICATION_MODE\ | \log\ (default) or \live\. |
| \EMAIL_PROVIDER_API_KEY\ | Resend API Key (required for \live\ mode). |
| \EMAIL_SENDER\ | The "From" email address. |

## Notifications

StatusForge supports two notification modes, controlled by \NOTIFICATION_MODE\:

1. **\log\ (Default)**: Emulates sending emails by logging the payload and recipient to the console. Perfect for local development.
2. **\live\**: Sends real emails via Resend. Requires \EMAIL_PROVIDER_API_KEY\ to be configured.

## Testing

**Backend** (Requires a running local database and Redis):
\\\ash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest tests
\\\

**Frontend**:
\\\ash
cd frontend
npm run test
\\\

## Deployment Guidance

StatusForge is designed to be fully deployable on free-tier infrastructure for small teams:

- **Frontend**: Deploy to **Vercel** or **Netlify**. Ensure \NEXT_PUBLIC_API_URL\ points to your backend production URL.
- **Backend**: Deploy the FastAPI app and the ARQ worker as two separate services on **Render** or **Railway**. Both services should use the exact same environment variables.
- **Database**: Use **Supabase** or **Neon** for free-tier managed PostgreSQL.
- **Redis**: Use **Upstash** for free-tier managed serverless Redis.
- **Email**: Use **Resend** (free tier includes 3,000 emails/month). 

*Note: Redis is required for background workers, but the public API will gracefully degrade if the Redis cache is temporarily unavailable.*
