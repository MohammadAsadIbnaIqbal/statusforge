from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.database import get_session
from app.core.dependencies import require_organization_member
from app.models.membership import Membership
from app.models.subscriber import Subscriber

router = APIRouter(tags=["Subscribers"], prefix="/subscribers")

@router.get("/confirm/{token}", status_code=status.HTTP_200_OK)
async def confirm_subscription(token: str, session: AsyncSession = Depends(get_session)):
    sub = (await session.exec(select(Subscriber).where(Subscriber.confirmation_token == token))).first()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Invalid confirmation link")
        
    if sub.confirmation_token_expires_at:
        expires_at = sub.confirmation_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=410, detail="Confirmation link has expired. Please subscribe again.")
        
    sub.is_confirmed = True
    sub.confirmation_token = None
    sub.confirmation_token_expires_at = None
    
    session.add(sub)
    await session.commit()
    
    return {"message": "Subscription confirmed!"}

@router.get("/unsubscribe/{token}", status_code=status.HTTP_200_OK)
async def unsubscribe(token: str, session: AsyncSession = Depends(get_session)):
    sub = (await session.exec(select(Subscriber).where(Subscriber.unsubscribe_token == token))).first()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Invalid unsubscribe link")
        
    await session.delete(sub)
    await session.commit()
    
    return {"message": "Successfully unsubscribed."}

@router.get("", status_code=status.HTTP_200_OK)
async def list_subscribers(
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    subs = (await session.exec(select(Subscriber).where(Subscriber.organization_id == membership.organization_id))).all()
    
    return [
        {
            "id": s.id,
            "email": s.email,
            "is_confirmed": s.is_confirmed,
            "created_at": s.created_at.isoformat()
        } for s in subs
    ]
