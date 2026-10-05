import asyncio
import logging
from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arq_worker")

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.database import engine
from app.models.incident import Incident, IncidentUpdate, IncidentServiceLink
from app.models.service import Service
from app.models.subscriber import Subscriber
from app.models.organization import Organization
from app.services.email_service import get_email_service

async def send_welcome_email_task(ctx, email: str, username: str):
    logger.info(f"[ARQ WORKER] Sending welcome email to {username} ({email})...")
    email_service = get_email_service()

    subject = f"Welcome to StatusForge, {username}!"
    text_body = f"Hello {username},\n\nWelcome to StatusForge! You can now start creating your services and tracking incidents.\n\nBest,\nStatusForge Team"
    html_body = f"<h3>Hello {username},</h3><p>Welcome to <strong>StatusForge</strong>! You can now start creating your services and tracking incidents.</p><p>Best,<br/>StatusForge Team</p>"

    await email_service.send_email(email, subject, html_body, text_body)
    return {"status": "sent", "recipient": email}

async def send_invitation_email_task(ctx, email: str, token: str):
    logger.info(f"[ARQ WORKER] Sending invitation email to {email}")
    email_service = get_email_service()

    accept_url = f"{settings.FRONTEND_URL}/invitations/accept?token={token}"
    subject = "You have been invited to join an organization on StatusForge"

    text_body = f"You have been invited to join an organization on StatusForge.\n\nAccept Invitation: {accept_url}\n"
    html_body = f"<p>You have been invited to join an organization on StatusForge.</p><p><a href='{accept_url}'>Accept Invitation</a></p>"

    await email_service.send_email(email, subject, html_body, text_body)
    return {"status": "sent", "recipient": email}

async def invalidate_cache(ctx, cache_key: str):
    logger.info(f"[ARQ WORKER] Invalidating cache key {cache_key}...")
    try:
        await ctx["redis"].delete(cache_key)
    except Exception as e:
        logger.error(f"[ARQ WORKER] Cache invalidation failed: {e}")

async def notify_subscribers(ctx, incident_id: int):
    logger.info(f"[ARQ WORKER] Sending notifications for incident {incident_id}")
    email_service = get_email_service()

    async with AsyncSession(engine) as session:
        incident = (await session.exec(select(Incident).where(Incident.id == incident_id))).first()
        if not incident:
            return

        org = (await session.exec(select(Organization).where(Organization.id == incident.organization_id))).first()
        if not org:
            return

        latest_update = (await session.exec(select(IncidentUpdate).where(IncidentUpdate.incident_id == incident_id).order_by(IncidentUpdate.created_at.desc()))).first()

        links = (await session.exec(select(IncidentServiceLink).where(IncidentServiceLink.incident_id == incident_id))).all()
        service_ids = [l.service_id for l in links]
        services = []
        for sid in service_ids:
            s = (await session.exec(select(Service).where(Service.id == sid))).first()
            if s: services.append(s.name)

        services_str = ", ".join(services) if services else "None"

        subject = f"[{org.name}] Incident Update: {incident.title}"

        public_url = f"{settings.FRONTEND_URL}/status/{org.slug}"

        text_body = f"""An incident has been updated for {org.name}.

Title: {incident.title}
Status: {incident.status}
Impact: {incident.impact}
Affected Services: {services_str}
Latest Update: {latest_update.message if latest_update else 'N/A'}
Timestamp: {incident.updated_at.isoformat()}

View status page: {public_url}
"""

        html_body = f"""<h2>{org.name} Incident Update</h2>
<p><strong>Title:</strong> {incident.title}</p>
<p><strong>Status:</strong> {incident.status}</p>
<p><strong>Impact:</strong> {incident.impact}</p>
<p><strong>Affected Services:</strong> {services_str}</p>
<p><strong>Latest Update:</strong> {latest_update.message if latest_update else 'N/A'}</p>
<p><strong>Timestamp:</strong> {incident.updated_at.isoformat()}</p>
<p><a href="{public_url}">View Status Page</a></p>
"""

        subscribers = (await session.exec(select(Subscriber).where(Subscriber.organization_id == incident.organization_id, Subscriber.is_confirmed == True))).all()

        for sub in subscribers:
            unsub_url = f"{settings.FRONTEND_URL}/subscribers/unsubscribe/{sub.unsubscribe_token}"
            sub_text_body = text_body + f"\n\nUnsubscribe: {unsub_url}"
            sub_html_body = html_body + f"<p><small><a href='{unsub_url}'>Unsubscribe</a></small></p>"

            try:
                await email_service.send_email(sub.email, subject, sub_html_body, sub_text_body)
            except Exception as e:
                logger.error(f"[ARQ WORKER] Failed to send notification to {sub.email}: {e}")

    return {"status": "sent", "incident_id": incident_id}

async def send_confirmation_email_task(ctx, email: str, token: str, org_name: str, org_slug: str):
    logger.info(f"[ARQ WORKER] Sending confirmation email to {email}")
    email_service = get_email_service()

    confirm_url = f"{settings.FRONTEND_URL}/subscribers/confirm/{token}"
    subject = f"Confirm your subscription to {org_name}"

    text_body = f"""Please confirm your subscription to status updates for {org_name}.

This link will expire in 24 hours.

Confirm Subscription: {confirm_url}
"""

    html_body = f"""<h3>Confirm your subscription to {org_name}</h3>
<p>Please confirm your subscription to receive status updates.</p>
<p>This link will expire in 24 hours.</p>
<p><a href="{confirm_url}">Confirm Subscription</a></p>
"""
    await email_service.send_email(email, subject, html_body, text_body)

def get_redis_settings(fast_fail: bool = False):
    url = settings.REDIS_URL.replace("redis://", "")
    if "@" in url:
        url = url.split("@")[1]
    parts = url.split(":")
    host = parts[0]
    port = int(parts[1].split("/")[0]) if len(parts) > 1 else 6379

    if fast_fail:
        return RedisSettings(host=host, port=port, conn_retries=0, conn_timeout=0.1)
    return RedisSettings(host=host, port=port)

class WorkerSettings:
    functions = [
        send_welcome_email_task,
        send_invitation_email_task,
        invalidate_cache,
        notify_subscribers,
        send_confirmation_email_task
    ]
    redis_settings = get_redis_settings()
