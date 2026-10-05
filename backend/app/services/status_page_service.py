from datetime import datetime, timezone, timedelta
import json
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, col
from fastapi import HTTPException
from app.models.organization import Organization
from app.models.service import Service, ServiceStatus
from app.models.incident import Incident, IncidentStatus, IncidentUpdate, IncidentServiceLink
from app.worker import get_redis_settings
from arq import create_pool

STATUS_WEIGHTS = {
    ServiceStatus.MAJOR_OUTAGE: 4,
    ServiceStatus.PARTIAL_OUTAGE: 3,
    ServiceStatus.DEGRADED_PERFORMANCE: 2,
    ServiceStatus.UNDER_MAINTENANCE: 1,
    ServiceStatus.OPERATIONAL: 0
}

async def fetch_public_status(session: AsyncSession, org_slug: str):
    org = (await session.exec(select(Organization).where(Organization.slug == org_slug))).first()
    if not org:
        raise HTTPException(status_code=404, detail="Status page not found")
        
    services = (await session.exec(
        select(Service).where(Service.organization_id == org.id, Service.is_visible == True).order_by(Service.display_order, Service.created_at)
    )).all()
    
    overall_status = ServiceStatus.OPERATIONAL
    if services:
        highest = max(services, key=lambda s: STATUS_WEIGHTS[s.current_status])
        overall_status = highest.current_status
        
    active_incidents_stmt = select(Incident).where(
        Incident.organization_id == org.id, 
        Incident.status != IncidentStatus.RESOLVED
    ).order_by(col(Incident.created_at).desc())
    active_incidents = (await session.exec(active_incidents_stmt)).all()
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_incidents_stmt = select(Incident).where(
        Incident.organization_id == org.id,
        Incident.status == IncidentStatus.RESOLVED,
        Incident.resolved_at >= seven_days_ago
    ).order_by(col(Incident.resolved_at).desc())
    recent_incidents = (await session.exec(recent_incidents_stmt)).all()
    
    async def serialize_incident(inc):
        updates = (await session.exec(select(IncidentUpdate).where(IncidentUpdate.incident_id == inc.id).order_by(col(IncidentUpdate.created_at).desc()))).all()
        links = (await session.exec(select(IncidentServiceLink).where(IncidentServiceLink.incident_id == inc.id))).all()
        s_ids = [l.service_id for l in links]
        affected_services = [s for s in services if s.id in s_ids]
        
        return {
            "id": inc.id,
            "title": inc.title,
            "impact": inc.impact,
            "status": inc.status,
            "created_at": inc.created_at.isoformat(),
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
            "services": [{"id": s.id, "name": s.name} for s in affected_services],
            "updates": [
                {
                    "status": u.status,
                    "message": u.message,
                    "created_at": u.created_at.isoformat()
                } for u in updates
            ]
        }
        
    active_payload = [await serialize_incident(i) for i in active_incidents]
    recent_payload = [await serialize_incident(i) for i in recent_incidents]
    
    return {
        "organization": {
            "name": org.name,
            "slug": org.slug
        },
        "overall_status": overall_status,
        "services": [
            {
                "id": s.id,
                "name": s.name,
                "status": s.current_status,
                "description": s.description
            } for s in services
        ],
        "active_incidents": active_payload,
        "recent_incidents": recent_payload
    }

async def get_cached_public_status(session: AsyncSession, org_slug: str):
    cache_key = f"statusforge:status:{org_slug}"
    redis = None
    try:
        redis = await create_pool(get_redis_settings(fast_fail=True))
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass 
        
    data = await fetch_public_status(session, org_slug)
    
    if redis:
        try:
            await redis.setex(cache_key, 30, json.dumps(data))
        except Exception:
            pass
            
    return data
