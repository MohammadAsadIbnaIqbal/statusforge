import sqlalchemy as sa
from datetime import datetime, timezone
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, col
from fastapi import HTTPException, status
from typing import Any

from app.models.incident import (
    Incident, IncidentCreate, IncidentUpdateCreate,
    IncidentServiceLink, IncidentUpdate, IncidentStatus
)
from app.models.service import Service
from app.models.organization import Organization
from app.models.user import User
from app.services.status_service import recompute_service_status
from app.worker import get_redis_settings
from arq import create_pool

async def create_incident(session: AsyncSession, organization: Organization, user: User, incident_in: IncidentCreate) -> Incident:
    if not incident_in.service_ids:
        raise HTTPException(status_code=422, detail="At least one service must be affected.")
        
    for sid in incident_in.service_ids:
        service = (await session.exec(select(Service).where(Service.id == sid, Service.organization_id == organization.id))).first()
        if not service:
            raise HTTPException(status_code=403, detail=f"Service ID {sid} does not exist or does not belong to this organization.")
            
    new_incident = Incident(
        title=incident_in.title,
        status=incident_in.status,
        impact=incident_in.impact,
        organization_id=organization.id,
        created_by_user_id=user.id
    )
    session.add(new_incident)
    await session.flush()
    
    for sid in incident_in.service_ids:
        link = IncidentServiceLink(incident_id=new_incident.id, service_id=sid)
        session.add(link)
        
    initial_update = IncidentUpdate(
        incident_id=new_incident.id,
        status=new_incident.status,
        message=incident_in.message,
        created_by_user_id=user.id
    )
    session.add(initial_update)
    
    for sid in incident_in.service_ids:
        await recompute_service_status(session, sid)
        
    await session.commit()
    await session.refresh(new_incident)

    try:
        redis = await create_pool(get_redis_settings(fast_fail=True))
        await redis.enqueue_job("invalidate_cache", f"statusforge:status:{organization.slug}")
        await redis.enqueue_job("notify_subscribers", incident_id=new_incident.id)
    except Exception:
        pass 

    return new_incident

async def update_incident(session: AsyncSession, organization: Organization, user: User, incident_id: int, update_in: IncidentUpdateCreate) -> Incident:
    stmt = select(Incident).where(Incident.id == incident_id, Incident.organization_id == organization.id).with_for_update()
    incident = (await session.exec(stmt)).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    if incident.status == IncidentStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Cannot update a resolved incident.")
        
    new_update = IncidentUpdate(
        incident_id=incident.id,
        status=update_in.status,
        message=update_in.message,
        created_by_user_id=user.id
    )
    session.add(new_update)
    
    incident.status = update_in.status
    incident.updated_at = datetime.now(timezone.utc)
    if update_in.status == IncidentStatus.RESOLVED:
        incident.resolved_at = datetime.now(timezone.utc)
        
    session.add(incident)
    await session.flush()
    
    links = (await session.exec(select(IncidentServiceLink).where(IncidentServiceLink.incident_id == incident.id))).all()
    for link in links:
        await recompute_service_status(session, link.service_id)
        
    await session.commit()
    await session.refresh(incident)

    try:
        redis = await create_pool(get_redis_settings(fast_fail=True))
        await redis.enqueue_job("invalidate_cache", f"statusforge:status:{organization.slug}")
        await redis.enqueue_job("notify_subscribers", incident_id=incident.id)
    except Exception:
        pass

    return incident

async def get_incidents(
    session: AsyncSession, 
    organization: Organization, 
    limit: int = 100, 
    offset: int = 0, 
    status_filter: str | None = None
) -> dict[str, Any]:
    stmt = select(Incident).where(Incident.organization_id == organization.id)
    
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)
        
    stmt = stmt.order_by(
        col(Incident.resolved_at).is_(None).desc(),
        col(Incident.created_at).desc()
    )
    
    total_stmt = select(sa.func.count()).select_from(stmt.subquery())
    total = (await session.exec(total_stmt)).one()
    
    stmt = stmt.limit(limit).offset(offset)
    incidents = (await session.exec(stmt)).all()
    
    items = []
    for inc in incidents:
        links = (await session.exec(select(IncidentServiceLink).where(IncidentServiceLink.incident_id == inc.id))).all()
        s_ids = [l.service_id for l in links]
        services = (await session.exec(select(Service).where(Service.id.in_(s_ids)))).all() if s_ids else []
        
        updates = (await session.exec(select(IncidentUpdate).where(IncidentUpdate.incident_id == inc.id).order_by(col(IncidentUpdate.created_at).desc()))).all()
        
        items.append({
            **inc.model_dump(),
            "services": services,
            "updates": updates
        })
        
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }

async def get_incident(session: AsyncSession, organization: Organization, incident_id: int) -> dict[str, Any]:
    inc = (await session.exec(select(Incident).where(Incident.id == incident_id, Incident.organization_id == organization.id))).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    links = (await session.exec(select(IncidentServiceLink).where(IncidentServiceLink.incident_id == inc.id))).all()
    s_ids = [l.service_id for l in links]
    services = (await session.exec(select(Service).where(Service.id.in_(s_ids)))).all() if s_ids else []
    
    updates = (await session.exec(select(IncidentUpdate).where(IncidentUpdate.incident_id == inc.id).order_by(col(IncidentUpdate.created_at).desc()))).all()
    
    return {
        **inc.model_dump(),
        "services": services,
        "updates": updates
    }
