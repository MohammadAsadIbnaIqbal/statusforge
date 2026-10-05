import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List

from app.core.database import get_session
from app.core.dependencies import require_organization_admin, require_organization_owner, get_current_user_firebase
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, Role
from app.models.invitation import Invitation, InvitationResponse
from pydantic import BaseModel, EmailStr
from app.worker import get_redis_settings
from arq import create_pool

router = APIRouter(tags=["Invitations"], prefix="/invitations")

class InviteCreate(BaseModel):
    email: EmailStr
    role: Role = Role.MEMBER

@router.post("", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invite_in: InviteCreate,
    membership: Membership = Depends(require_organization_admin),
    session: AsyncSession = Depends(get_session)
):
    if invite_in.role == Role.OWNER:
        raise HTTPException(status_code=403, detail="Cannot invite users as OWNER")
    if invite_in.role == Role.ADMIN and membership.role != Role.OWNER:
        raise HTTPException(status_code=403, detail="Only OWNER can invite ADMIN")

    user_stmt = select(User).where(User.email == invite_in.email)
    invited_user = (await session.exec(user_stmt)).first()
    if invited_user:
        member_stmt = select(Membership).where(
            Membership.user_id == invited_user.id,
            Membership.organization_id == membership.organization_id
        )
        if (await session.exec(member_stmt)).first():
            raise HTTPException(status_code=400, detail="User is already a member")

    inv_stmt = select(Invitation).where(
        Invitation.organization_id == membership.organization_id,
        Invitation.email == invite_in.email,
        Invitation.accepted_at == None,
        Invitation.revoked_at == None
    )
    existing_inv = (await session.exec(inv_stmt)).first()
    if existing_inv and existing_inv.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Active invitation already exists")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    inv = Invitation(
        organization_id=membership.organization_id,
        email=invite_in.email,
        role=invite_in.role.value,
        token_hash=token_hash,
        invited_by_user_id=membership.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )

    session.add(inv)
    await session.commit()
    await session.refresh(inv)

    try:
        redis = await create_pool(get_redis_settings(fast_fail=True))
        await redis.enqueue_job("send_invitation_email_task", email=invite_in.email, token=raw_token)
    except Exception:
        pass

    return inv

@router.get("", response_model=List[InvitationResponse])
async def list_invitations(
    membership: Membership = Depends(require_organization_admin),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Invitation).where(
        Invitation.organization_id == membership.organization_id,
        Invitation.accepted_at == None,
        Invitation.revoked_at == None
    )
    invitations = (await session.exec(stmt)).all()
    return invitations

@router.post("/{token}/accept", status_code=status.HTTP_200_OK)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user_firebase),
    session: AsyncSession = Depends(get_session)
):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    stmt = select(Invitation).where(Invitation.token_hash == token_hash)
    inv = (await session.exec(stmt)).first()

    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    if inv.accepted_at or inv.revoked_at:
        raise HTTPException(status_code=400, detail="Invitation is no longer active")
    if inv.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitation has expired")
    if inv.email != current_user.email:
        raise HTTPException(status_code=403, detail="Invitation email does not match your account")

    new_member = Membership(
        user_id=current_user.id,
        organization_id=inv.organization_id,
        role=Role(inv.role)
    )
    session.add(new_member)

    inv.accepted_at = datetime.now(timezone.utc)
    session.add(inv)

    await session.commit()
    return {"message": "Invitation accepted successfully"}

@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: int,
    membership: Membership = Depends(require_organization_admin),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Invitation).where(
        Invitation.id == invitation_id,
        Invitation.organization_id == membership.organization_id,
        Invitation.accepted_at == None,
        Invitation.revoked_at == None
    )
    inv = (await session.exec(stmt)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if inv.role == Role.ADMIN.value and membership.role != Role.OWNER:
        raise HTTPException(status_code=403, detail="Only OWNER can revoke ADMIN invitations")

    inv.revoked_at = datetime.now(timezone.utc)
    session.add(inv)
    await session.commit()

@router.post("/{invitation_id}/resend", status_code=status.HTTP_200_OK)
async def resend_invitation(
    invitation_id: int,
    membership: Membership = Depends(require_organization_admin),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Invitation).where(
        Invitation.id == invitation_id,
        Invitation.organization_id == membership.organization_id,
        Invitation.accepted_at == None,
        Invitation.revoked_at == None
    )
    inv = (await session.exec(stmt)).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if inv.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        inv.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    raw_token = secrets.token_urlsafe(32)
    inv.token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    session.add(inv)
    await session.commit()

    try:
        redis = await create_pool(get_redis_settings(fast_fail=True))
        await redis.enqueue_job("send_invitation_email_task", email=inv.email, token=raw_token)
    except Exception:
        pass

    return {"message": "Invitation resent"}
