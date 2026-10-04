from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from app.core.database import get_session
from app.core.dependencies import get_current_user_firebase, require_organization_owner
from app.models.user import User
from app.models.organization import Organization, OrganizationResponse
from app.models.membership import Membership, MembershipResponse, Role

router = APIRouter(tags=["Organizations"])

@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_user_firebase),
    session: AsyncSession = Depends(get_session)
):
    statement = select(Organization).join(Membership).where(Membership.user_id == current_user.id)
    orgs = (await session.exec(statement)).all()
    return orgs

@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_user_firebase),
    session: AsyncSession = Depends(get_session)
):
    statement = select(Organization).join(Membership).where(
        Membership.user_id == current_user.id,
        Organization.id == org_id
    )
    org = (await session.exec(statement)).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.get("/organizations/{org_id}/members", response_model=List[MembershipResponse])
async def list_members(
    org_id: int,
    current_user: User = Depends(get_current_user_firebase),
    session: AsyncSession = Depends(get_session)
):
    # Verify membership
    verify_stmt = select(Membership).where(
        Membership.user_id == current_user.id,
        Membership.organization_id == org_id
    )
    if not (await session.exec(verify_stmt)).first():
        raise HTTPException(status_code=403, detail="Not a member")
        
    statement = select(Membership).where(Membership.organization_id == org_id)
    memberships = (await session.exec(statement)).all()
    return memberships
