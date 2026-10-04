import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, status, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.database import get_session
from app.models.organization import Organization
from app.models.subscriber import Subscriber, SubscriberCreate
from app.services.status_page_service import get_cached_public_status
from app.worker import get_redis_settings
from arq import create_pool
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(tags=["Public Status"])
limiter = Limiter(key_func=get_remote_address)

@router.get("/status/{org_slug}", status_code=status.HTTP_200_OK)
async def get_status_page(
    org_slug: str,
    session: AsyncSession = Depends(get_session)
):
    return await get_cached_public_status(session, org_slug)

@router.post("/status/{org_slug}/subscribe", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def subscribe_to_status(
    request: Request,
    org_slug: str,
    subscriber_in: SubscriberCreate,
    session: AsyncSession = Depends(get_session)
):
    org = (await session.exec(select(Organization).where(Organization.slug == org_slug))).first()
    if not org:
        raise HTTPException(status_code=404, detail="Status page not found")
        
    existing = (await session.exec(
        select(Subscriber).where(Subscriber.organization_id == org.id, Subscriber.email == subscriber_in.email)
    )).first()
    
    if existing:
        if not existing.is_confirmed and existing.confirmation_token_expires_at:
            expires_at = existing.confirmation_token_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
                
            if datetime.now(timezone.utc) > expires_at:
                await session.delete(existing)
                await session.flush()
            else:
                raise HTTPException(status_code=409, detail="Email already subscribed")
        else:
            raise HTTPException(status_code=409, detail="Email already subscribed")
            
    conf_token = secrets.token_urlsafe(32)
    unsub_token = secrets.token_urlsafe(32)
    
    new_sub = Subscriber(
        organization_id=org.id,
        email=subscriber_in.email,
        confirmation_token=conf_token,
        confirmation_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        unsubscribe_token=unsub_token
    )
    
    session.add(new_sub)
    await session.commit()
    
    try:
        redis = await create_pool(get_redis_settings(fast_fail=True))
        await redis.enqueue_job(
            "send_confirmation_email_task", 
            email=new_sub.email, 
            token=conf_token,
            org_name=org.name,
            org_slug=org.slug
        )
    except Exception:
        pass
        
    return {"message": "Please check your email to confirm your subscription."}
