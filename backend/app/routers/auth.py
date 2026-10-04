from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import re

from app.core.database import get_session
from app.core.dependencies import verify_firebase_token, get_current_user_firebase
from app.models.user import User, UserResponse
from app.models.organization import Organization
from app.models.membership import Membership, Role
from pydantic import BaseModel

router = APIRouter(tags=["Authentication"])

class BootstrapRequest(BaseModel):
    organization_name: str | None = None

async def generate_unique_slug(session: AsyncSession, base_name: str) -> str:
    base_slug = re.sub(r'[^a-z0-9]+', '-', base_name.lower()).strip('-')
    if not base_slug:
        base_slug = "org"
        
    slug = base_slug[:100]
    counter = 1
    while True:
        statement = select(Organization).where(Organization.slug == slug)
        if not (await session.exec(statement)).first():
            return slug
        counter += 1
        suffix = f"-{counter}"
        slug = f"{base_slug[:100 - len(suffix)]}{suffix}"

@router.post("/auth/bootstrap", response_model=UserResponse)
async def bootstrap_user(
    request_data: BootstrapRequest,
    decoded_token: dict = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session)
):
    firebase_uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    display_name = decoded_token.get("name")
    photo_url = decoded_token.get("picture")
    email_verified = decoded_token.get("email_verified", False)
    
    if not firebase_uid or not email:
        raise HTTPException(status_code=400, detail="Invalid token data")

    # Check if user already exists
    statement = select(User).where(User.firebase_uid == firebase_uid)
    existing_user = (await session.exec(statement)).first()
    
    if existing_user:
        # Update profile if needed
        existing_user.display_name = display_name or existing_user.display_name
        existing_user.photo_url = photo_url or existing_user.photo_url
        existing_user.email_verified = email_verified
        await session.commit()
        await session.refresh(existing_user)
        return existing_user

    # Create new user
    new_user = User(
        firebase_uid=firebase_uid,
        email=email,
        display_name=display_name,
        photo_url=photo_url,
        email_verified=email_verified
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    # First time user setup -> Create Organization
    org_name = request_data.organization_name or f"{email.split('@')[0]}'s Organization"
    org_slug = await generate_unique_slug(session, org_name)
    
    new_org = Organization(
        name=org_name,
        slug=org_slug,
        created_by=new_user.id
    )
    session.add(new_org)
    await session.commit()
    await session.refresh(new_org)
    
    # Create OWNER membership
    membership = Membership(
        user_id=new_user.id,
        organization_id=new_org.id,
        role=Role.OWNER
    )
    session.add(membership)
    await session.commit()
    
    return new_user

@router.get("/auth/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user_firebase)):
    return current_user
