import asyncio
import logging
from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arq_worker")


# Task: Asynchronous Email Delivery Task
async def send_welcome_email_task(ctx, email: str, username: str):
    logger.info(f"[ARQ WORKER] Starting background email job for {username} ({email})...")
    # Simulate non-blocking network delay (e.g. SendGrid / AWS SES API call)
    await asyncio.sleep(3)
    logger.info(f"[ARQ WORKER] Successfully sent welcome email to {username} ({email})!")
    return {"status": "sent", "recipient": email}


# Parse REDIS_URL into ARQ settings
def get_redis_settings():
    # Extracts host and port from redis://host:port
    url = settings.REDIS_URL.replace("redis://", "")
    if "@" in url:
        url = url.split("@")[1]
    parts = url.split(":")
    host = parts[0]
    port = int(parts[1].split("/")[0]) if len(parts) > 1 else 6379
    return RedisSettings(host=host, port=port)


# Worker Settings Class required by ARQ CLI
class WorkerSettings:
    functions = [send_welcome_email_task]
    redis_settings = get_redis_settings()