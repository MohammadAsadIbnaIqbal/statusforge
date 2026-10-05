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


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: int,
    membership: Membership = Depends(require_organization_owner),
    session: AsyncSession = Depends(get_session)
):
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    org = (await session.exec(select(Organization).where(Organization.id == org_id))).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Handle dependent resources safely
    from app.models.invitation import Invitation
    from app.models.service import Service
    from app.models.incident import Incident, IncidentUpdate, IncidentServiceLink
    from app.models.subscriber import Subscriber

    # 1. Delete incident updates and links
    incidents = (await session.exec(select(Incident).where(Incident.organization_id == org_id))).all()
    for inc in incidents:
        # Delete links
        links = (await session.exec(select(IncidentServiceLink).where(IncidentServiceLink.incident_id == inc.id))).all()
        for link in links:
            await session.delete(link)
        # Delete updates
        updates = (await session.exec(select(IncidentUpdate).where(IncidentUpdate.incident_id == inc.id))).all()
        for up in updates:
            await session.delete(up)
        # Delete incident
        await session.delete(inc)

    # 2. Delete Services
    services = (await session.exec(select(Service).where(Service.organization_id == org_id))).all()
    for s in services:
        await session.delete(s)

    # 3. Delete Subscribers
    subs = (await session.exec(select(Subscriber).where(Subscriber.organization_id == org_id))).all()
    for sub in subs:
        await session.delete(sub)

    # 4. Delete Invitations
    invs = (await session.exec(select(Invitation).where(Invitation.organization_id == org_id))).all()
    for inv in invs:
        await session.delete(inv)

    # 5. Delete Memberships
    mems = (await session.exec(select(Membership).where(Membership.organization_id == org_id))).all()
    for mem in mems:
        await session.delete(mem)

    # 6. Delete Organization
    await session.delete(org)

    await session.commit()

from pydantic import BaseModel
class TransferOwnershipRequest(BaseModel):
    new_owner_user_id: int

@router.post("/organizations/{org_id}/transfer_ownership", status_code=status.HTTP_200_OK)
async def transfer_ownership(
    org_id: int,
    req: TransferOwnershipRequest,
    membership: Membership = Depends(require_organization_owner),
    session: AsyncSession = Depends(get_session)
):
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if membership.user_id == req.new_owner_user_id:
        raise HTTPException(status_code=400, detail="Cannot transfer ownership to yourself")

    new_owner_membership = (await session.exec(
        select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == req.new_owner_user_id
        )
    )).first()

    if not new_owner_membership:
        raise HTTPException(status_code=404, detail="User is not a member of this organization")

    # Transactional ownership swap
    new_owner_membership.role = Role.OWNER
    membership.role = Role.ADMIN

    session.add(new_owner_membership)
    session.add(membership)
    await session.commit()

    return {"message": "Ownership transferred successfully"}
