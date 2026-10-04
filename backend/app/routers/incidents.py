from fastapi import APIRouter, Depends, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

from app.core.database import get_session
from app.core.dependencies import require_organization_member, get_organization_from_header, get_current_user_firebase
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, Role
from app.models.incident import IncidentCreate, IncidentUpdateCreate, Incident, IncidentResponse
from app.services.incident_service import create_incident, update_incident, get_incidents, get_incident
from fastapi import HTTPException

router = APIRouter(tags=["Incidents"], prefix="/incidents")

T = TypeVar('T')
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

def ensure_manage_permission(membership: Membership):
    if membership.role not in (Role.OWNER, Role.ADMIN, Role.MEMBER):
        raise HTTPException(status_code=403, detail="Not authorized to manage incidents")

@router.post("", response_model=Incident, status_code=status.HTTP_201_CREATED)
async def api_create_incident(
    incident_data: IncidentCreate,
    current_user: User = Depends(get_current_user_firebase),
    organization: Organization = Depends(get_organization_from_header),
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    ensure_manage_permission(membership)
    return await create_incident(session, organization, current_user, incident_data)

@router.post("/{incident_id}/updates", response_model=Incident, status_code=status.HTTP_200_OK)
async def api_update_incident(
    incident_id: int,
    update_data: IncidentUpdateCreate,
    current_user: User = Depends(get_current_user_firebase),
    organization: Organization = Depends(get_organization_from_header),
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    ensure_manage_permission(membership)
    return await update_incident(session, organization, current_user, incident_id, update_data)

@router.get("", response_model=PaginatedResponse[IncidentResponse], status_code=status.HTTP_200_OK)
async def api_get_incidents(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status"),
    organization: Organization = Depends(get_organization_from_header),
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    return await get_incidents(session, organization, limit, offset, status_filter)

@router.get("/{incident_id}", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
async def api_get_incident(
    incident_id: int,
    organization: Organization = Depends(get_organization_from_header),
    membership: Membership = Depends(require_organization_member),
    session: AsyncSession = Depends(get_session)
):
    return await get_incident(session, organization, incident_id)
