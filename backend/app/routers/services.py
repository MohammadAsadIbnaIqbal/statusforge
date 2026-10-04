from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_session
from app.core.dependencies import require_organization_member, get_organization_from_header
from app.models.organization import Organization
from app.models.membership import Membership, Role
from app.models.service import Service, ServiceCreate, ServiceUpdate, ServiceResponse
from app.models.incident import Incident, IncidentServiceLink, IncidentStatus

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Services"], prefix="/services")

def ensure_manage_permission(membership: Membership):
    if membership.role not in (Role.OWNER, Role.ADMIN, Role.MEMBER):
        raise HTTPException(status_code=403, detail="Not authorized to manage services")

@router.get("", response_model=list[ServiceResponse])
async def list_services(
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    statement = select(Service).where(Service.organization_id == membership.organization_id).order_by(
        Service.display_order.asc(),
        Service.created_at.asc()
    )
    results = await session.exec(statement)
    return results.all()

@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_service(
    request: Request,
    service_data: ServiceCreate,
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    ensure_manage_permission(membership)
    
    # Enforce max 20 services per org
    count_statement = select(func.count()).select_from(Service).where(Service.organization_id == membership.organization_id)
    count_result = (await session.exec(count_statement)).one()
    count = count_result[0] if isinstance(count_result, tuple) else count_result
    
    if count >= 20:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Maximum number of services (20) reached for this organization."
        )

    new_service = Service(
        **service_data.model_dump(),
        organization_id=membership.organization_id
    )

    session.add(new_service)
    await session.commit()
    await session.refresh(new_service)
    return new_service

@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    statement = select(Service).where(Service.id == service_id, Service.organization_id == membership.organization_id)
    service = (await session.exec(statement)).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    return service

@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    ensure_manage_permission(membership)
    
    statement = select(Service).where(Service.id == service_id, Service.organization_id == membership.organization_id)
    service = (await session.exec(statement)).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    update_data = service_data.model_dump(exclude_unset=True)
    if update_data:
        for key, value in update_data.items():
            setattr(service, key, value)
        
        service.updated_at = datetime.now(timezone.utc)
        session.add(service)
        await session.commit()
        await session.refresh(service)
        
    return service

@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: int,
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    ensure_manage_permission(membership)
    
    statement = select(Service).where(Service.id == service_id, Service.organization_id == membership.organization_id)
    service = (await session.exec(statement)).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        
    # Check for active incidents
    incident_statement = select(Incident).join(IncidentServiceLink).where(
        IncidentServiceLink.service_id == service.id,
        Incident.status != IncidentStatus.RESOLVED
    )
    active_incident = (await session.exec(incident_statement)).first()
    if active_incident:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a service that is part of an active incident."
        )

    await session.delete(service)
    await session.commit()
