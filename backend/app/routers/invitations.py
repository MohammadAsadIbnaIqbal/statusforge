import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List

from app.core.database import get_session
from app.core.dependencies import require_organization_admin, get_current_user_firebase
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, Role
from app.models.invitation import Invitation, InvitationResponse
from pydantic import BaseModel, EmailStr

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
    # Check if user already in org
    user_stmt = select(User).where(User.email == invite_in.email)
    invited_user = (await session.exec(user_stmt)).first()
    if invited_user:
        member_stmt = select(Membership).where(
            Membership.user_id == invited_user.id,
            Membership.organization_id == membership.organization_id
        )
        if (await session.exec(member_stmt)).first():
            raise HTTPException(status_code=400, detail="User is already a member")
            
    # Check if active invitation exists
    inv_stmt = select(Invitation).where(
        Invitation.organization_id == membership.organization_id,
        Invitation.email == invite_in.email,
        Invitation.accepted_at == None,
        Invitation.revoked_at == None
    )
    existing_inv = (await session.exec(inv_stmt)).first()
    if existing_inv and existing_inv.expires_at > datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Active invitation already exists")
        
    token_hash = secrets.token_urlsafe(32)
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
    
    # Ideally send email here
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
    stmt = select(Invitation).where(Invitation.token_hash == token)
    inv = (await session.exec(stmt)).first()
    
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    if inv.accepted_at or inv.revoked_at:
        raise HTTPException(status_code=400, detail="Invitation is no longer active")
    if inv.expires_at < datetime.now(timezone.utc):
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
