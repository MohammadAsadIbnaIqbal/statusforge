from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import get_session
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.incident import IncidentCreate, IncidentUpdateCreate, Incident
from app.services.incident_service import create_incident, update_incident

router = APIRouter(tags=["Incidents"], prefix="/incidents")

@router.post("", response_model=Incident, status_code=status.HTTP_201_CREATED)
async def api_create_incident(
    incident_data: IncidentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    return await create_incident(session, current_user, incident_data)

@router.post("/{incident_id}/updates", response_model=Incident, status_code=status.HTTP_200_OK)
async def api_update_incident(
    incident_id: int,
    update_data: IncidentUpdateCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    return await update_incident(session, current_user, incident_id, update_data)

from typing import Any
from fastapi import Query
from app.models.incident import IncidentResponse
from app.services.incident_service import get_incidents, get_incident

# We need a paginated response model
from typing import Generic, TypeVar
from pydantic import BaseModel
T = TypeVar('T')
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

@router.get("", response_model=PaginatedResponse[IncidentResponse], status_code=status.HTTP_200_OK)
async def api_get_incidents(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    return await get_incidents(session, current_user, limit, offset, status)

@router.get("/{incident_id}", response_model=IncidentResponse, status_code=status.HTTP_200_OK)
async def api_get_incident(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    return await get_incident(session, current_user, incident_id)
