# CI/CD pipeline verification comment
import asyncio
import logging
from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from arq.worker import Worker
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlmodel import select

from app.core.config import settings
from app.core.database import engine
from app.routers import auth, services, incidents, public_status, subscribers, organizations, invitations
from app.worker import WorkerSettings  

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=1.0,  
        profiles_sample_rate=1.0,
        environment="production",
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("statusforge")

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up StatusForge API...")

    # 1. Initialize Redis Cache
    try:
        redis = aioredis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=True)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
        logger.info("Redis cache initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")

    # 2. 🚀 Start Embedded ARQ Worker in the background ($0/month)
    worker = None
    worker_task = None
    try:
        worker = Worker(
            functions=WorkerSettings.functions,
            redis_settings=WorkerSettings.redis_settings,
            handle_signals=False
        )
        worker_task = asyncio.create_task(worker.async_run())
        logger.info("Embedded ARQ Background Worker started successfully.")
    except Exception as e:
        logger.warning(f"Failed to start embedded ARQ Worker: {e}")

    yield

    if worker_task:
        logger.info("Shutting down ARQ Worker task...")
        worker_task.cancel()
        await asyncio.gather(worker_task, return_exceptions=True)
    if worker:
        try:
            await worker.close()
            logger.info("ARQ Worker closed.")
        except Exception as e:
            logger.warning(f"Failed to close ARQ worker: {e}")

    logger.info("Shutting down and disposing database engine...")
    await engine.dispose()


app = FastAPI(title="StatusForge API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    return {"message": "Welcome to StatusForge API! Visit /docs for interactive documentation."}

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Monitoring"])
@app.head("/health", status_code=status.HTTP_200_OK, tags=["Monitoring"], include_in_schema=False)
async def health_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        return {
            "status": "healthy",
            "database": "connected",
            "service": "statusforge-api"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


# Include Routers
app.include_router(auth.router)
app.include_router(services.router)
app.include_router(incidents.router)
app.include_router(public_status.router)
app.include_router(subscribers.router)
app.include_router(organizations.router)
app.include_router(invitations.router)
