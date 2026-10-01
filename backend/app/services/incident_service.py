import sqlalchemy as sa
from datetime import datetime, timezone
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, status
from app.models.incident import (
    Incident, IncidentCreate, IncidentUpdateCreate,
    IncidentServiceLink, IncidentUpdate, IncidentStatus
)
from app.models.service import Service
from app.models.user import User
from app.services.status_service import recompute_service_status
from app.worker import get_redis_settings
from arq import create_pool

async def create_incident(session: AsyncSession, user: User, incident_in: IncidentCreate) -> Incident:
    if not incident_in.service_ids:
        raise HTTPException(status_code=422, detail="At least one service must be affected.")
        
    # Validate ownership of all affected services
    for sid in incident_in.service_ids:
        service = (await session.exec(select(Service).where(Service.id == sid, Service.owner_id == user.id))).first()
        if not service:
            raise HTTPException(status_code=403, detail=f"Service ID {sid} does not exist or does not belong to you.")
            
    new_incident = Incident(
        title=incident_in.title,
        status=incident_in.status,
        impact=incident_in.impact,
        owner_id=user.id
    )
    session.add(new_incident)
    await session.flush()
    
    for sid in incident_in.service_ids:
        link = IncidentServiceLink(incident_id=new_incident.id, service_id=sid)
        session.add(link)
        
    initial_update = IncidentUpdate(
        incident_id=new_incident.id,
        status=new_incident.status,
        message=incident_in.message
    )
    session.add(initial_update)
    
    for sid in incident_in.service_ids:
        await recompute_service_status(session, sid)
        
    await session.commit()
    await session.refresh(new_incident)

    # Cache invalidation and notifications
    try:
        redis = await create_pool(get_redis_settings(fast_fail=True))
        await redis.enqueue_job("invalidate_cache", f"statusforge:status:{user.organization_slug}")
        await redis.enqueue_job("notify_subscribers", incident_id=new_incident.id)
    except Exception:
        pass # Background hook failure shouldn't fail the request

    return new_incident

async def update_incident(session: AsyncSession, user: User, incident_id: int, update_in: IncidentUpdateCreate) -> Incident:
    stmt = select(Incident).where(Incident.id == incident_id, Incident.owner_id == user.id).with_for_update()
    incident = (await session.exec(stmt)).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    if incident.status == IncidentStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Cannot update a resolved incident.")
        
    new_update = IncidentUpdate(
        incident_id=incident.id,
        status=update_in.status,
        message=update_in.message
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

    # Cache invalidation and notifications
    try:
        redis = await create_pool(get_redis_settings(fast_fail=True))
        await redis.enqueue_job("invalidate_cache", f"statusforge:status:{user.organization_slug}")
        await redis.enqueue_job("notify_subscribers", incident_id=incident.id)
    except Exception:
        pass

    return incident

from sqlmodel import col
from typing import Any

async def get_incidents(
    session: AsyncSession, 
    user: User, 
    limit: int = 100, 
    offset: int = 0, 
    status_filter: str | None = None
) -> dict[str, Any]:
    stmt = select(Incident).where(Incident.owner_id == user.id)
    
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)
        
    # Sort active first, then resolved, then by created_at desc
    # In SQLite/Postgres we can order by status != 'RESOLVED' DESC (or similar),
    # but let's just fetch and sort in memory if it's complex, or sort by resolved_at NULLS FIRST
    # Actually, a simple way:
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
        # fetch links
        links = (await session.exec(select(IncidentServiceLink).where(IncidentServiceLink.incident_id == inc.id))).all()
        s_ids = [l.service_id for l in links]
        services = (await session.exec(select(Service).where(Service.id.in_(s_ids)))).all() if s_ids else []
        
        # fetch updates
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

async def get_incident(session: AsyncSession, user: User, incident_id: int) -> dict[str, Any]:
    inc = (await session.exec(select(Incident).where(Incident.id == incident_id, Incident.owner_id == user.id))).first()
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

