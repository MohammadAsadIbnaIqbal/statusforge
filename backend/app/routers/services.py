from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_session
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.service import Service, ServiceCreate, ServiceUpdate, ServiceResponse
from app.models.incident import Incident, IncidentServiceLink, IncidentStatus

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Services"], prefix="/services")

@router.get("", response_model=list[ServiceResponse])
async def list_services(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    statement = select(Service).where(Service.owner_id == current_user.id).order_by(
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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Enforce max 20 services per user
    count_statement = select(func.count()).select_from(Service).where(Service.owner_id == current_user.id)
    count_result = (await session.exec(count_statement)).one()
    count = count_result[0] if isinstance(count_result, tuple) else count_result
    
    if count >= 20:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Maximum number of services (20) reached for this organization."
        )

    new_service = Service(
        **service_data.model_dump(),
        owner_id=current_user.id
    )

    session.add(new_service)
    await session.commit()
    await session.refresh(new_service)
    return new_service

@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    statement = select(Service).where(Service.id == service_id, Service.owner_id == current_user.id)
    service = (await session.exec(statement)).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    return service

@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    statement = select(Service).where(Service.id == service_id, Service.owner_id == current_user.id)
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
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    statement = select(Service).where(Service.id == service_id, Service.owner_id == current_user.id)
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
