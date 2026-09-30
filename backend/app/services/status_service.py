from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.models.service import Service, ServiceStatus
from app.models.incident import Incident, IncidentServiceLink, IncidentStatus, IncidentImpact

IMPACT_WEIGHTS = {
    IncidentImpact.CRITICAL: 4,
    IncidentImpact.MAJOR: 3,
    IncidentImpact.MINOR: 2,
    IncidentImpact.NONE: 1,
}

IMPACT_TO_STATUS = {
    IncidentImpact.CRITICAL: ServiceStatus.MAJOR_OUTAGE,
    IncidentImpact.MAJOR: ServiceStatus.PARTIAL_OUTAGE,
    IncidentImpact.MINOR: ServiceStatus.DEGRADED_PERFORMANCE,
    IncidentImpact.NONE: ServiceStatus.OPERATIONAL,
}

async def recompute_service_status(session: AsyncSession, service_id: int) -> ServiceStatus:
    """
    Recomputes and updates the current_status of a service based on active incidents.
    Returns the new status.
    Must be called within an active transaction.
    """
    # Fetch the service with an exclusive lock to prevent concurrent status race conditions
    statement = select(Service).where(Service.id == service_id).with_for_update()
    service = (await session.exec(statement)).first()
    
    if not service:
        return ServiceStatus.OPERATIONAL
        
    # Find all active incidents affecting this service
    incident_stmt = select(Incident).join(IncidentServiceLink).where(
        IncidentServiceLink.service_id == service_id,
        Incident.status != IncidentStatus.RESOLVED
    )
    active_incidents = (await session.exec(incident_stmt)).all()
    
    if not active_incidents:
        service.current_status = ServiceStatus.OPERATIONAL
    else:
        highest_impact = max(active_incidents, key=lambda i: IMPACT_WEIGHTS[i.impact]).impact
        service.current_status = IMPACT_TO_STATUS[highest_impact]
        
    session.add(service)
    return service.current_status
