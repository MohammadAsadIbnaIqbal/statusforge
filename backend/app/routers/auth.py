import re
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from app.core.database import get_session
from app.core.dependencies import verify_firebase_token, get_current_user_firebase
from app.models.user import User, UserResponse
from app.models.organization import Organization
from app.models.membership import Membership, Role

logger = logging.getLogger("statusforge.auth")
router = APIRouter(tags=["Authentication"])

class BootstrapRequest(BaseModel):
    organization_name: str | None = None

def _create_slug(base_name: str, counter: int) -> str:
    base_slug = re.sub(r'[^a-z0-9]+', '-', base_name.lower()).strip('-')
    if not base_slug:
        base_slug = "org"

    if counter == 1:
        return base_slug[:100]

    suffix = f"-{counter}"
    return f"{base_slug[:100 - len(suffix)]}{suffix}"

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

    # Fast path: check if user exists
    statement = select(User).where(User.firebase_uid == firebase_uid)
    existing_user = (await session.exec(statement)).first()

    if existing_user:
        existing_user.display_name = display_name or existing_user.display_name
        existing_user.photo_url = photo_url or existing_user.photo_url
        existing_user.email_verified = email_verified
        session.add(existing_user)
        await session.commit()
        await session.refresh(existing_user)
        return existing_user

    org_name = request_data.organization_name or f"{email.split('@')[0]}'s Organization"

    # Transactional bootstrap with retries for slug collisions
    max_retries = 10
    for attempt in range(1, max_retries + 1):
        try:
            # We must recreate the objects each retry because a failed session.commit()
            # invalidates the objects in the session.
            async with session.begin_nested():
                # Re-check user inside transaction to avoid race condition
                user_stmt = select(User).where(User.firebase_uid == firebase_uid)
                if (await session.exec(user_stmt)).first():
                    break # User created concurrently

                new_user = User(
                    firebase_uid=firebase_uid,
                    email=email,
                    display_name=display_name,
                    photo_url=photo_url,
                    email_verified=email_verified
                )
                session.add(new_user)
                await session.flush()

                org_slug = _create_slug(org_name, attempt)
                new_org = Organization(
                    name=org_name,
                    slug=org_slug,
                    created_by=new_user.id
                )
                session.add(new_org)
                await session.flush()

                membership = Membership(
                    user_id=new_user.id,
                    organization_id=new_org.id,
                    role=Role.OWNER
                )
                session.add(membership)
                await session.flush()

            # If we reach here, begin_nested committed successfully
            await session.commit()
            await session.refresh(new_user)
            return new_user

        except IntegrityError as e:
            await session.rollback()
            # If the error is about firebase_uid or email, another thread created the user
            if "firebase_uid" in str(e) or "email" in str(e):
                logger.info(f"Concurrent user creation for {firebase_uid}")
                break # Fall through to fetch existing user
            # If it's a slug collision, loop again
            if "slug" in str(e):
                if attempt == max_retries:
                    raise HTTPException(status_code=409, detail="Could not generate unique organization slug")
                continue
            raise e

    # Fallback fetch if user was created concurrently
    statement = select(User).where(User.firebase_uid == firebase_uid)
    existing_user = (await session.exec(statement)).first()
    if existing_user:
        return existing_user

    raise HTTPException(status_code=500, detail="Failed to bootstrap user")

@router.get("/auth/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user_firebase)):
    return current_user
