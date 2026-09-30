import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user import User
from app.models.service import Service, ServiceStatus
from app.models.incident import Incident, IncidentStatus, IncidentImpact, IncidentServiceLink
from app.models.subscriber import Subscriber

@pytest.mark.asyncio
async def test_create_and_query_models(client, setup_db):
    from app.core.database import get_session
    from app.main import app
    
    # Get the overridden session from dependency overrides
    session_generator = app.dependency_overrides[get_session]()
    session: AsyncSession = await session_generator.__anext__()
    
    # Create User
    user = User(
        username="org_owner",
        email="owner@org.com",
        organization_name="My Org",
        organization_slug="my-org",
        hashed_password="hash"
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    # Create Service
    service = Service(
        name="API",
        description="Core API",
        owner_id=user.id
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)
    
    # Create Incident
    incident = Incident(
        title="API Outage",
        impact=IncidentImpact.CRITICAL,
        owner_id=user.id
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)
    
    # Link Service to Incident
    link = IncidentServiceLink(incident_id=incident.id, service_id=service.id)
    session.add(link)
    await session.commit()
    
    # Create Subscriber
    subscriber = Subscriber(
        email="sub@test.com",
        owner_id=user.id,
        unsubscribe_token="token123"
    )
    session.add(subscriber)
    await session.commit()
    await session.refresh(subscriber)
    
    # Query relationships
    # Note: selectinload might be needed in real async code to load relationships, 
    # but here we can just verify the items exist in DB
    
    db_user = (await session.exec(select(User).where(User.username == "org_owner"))).first()
    assert db_user is not None
    assert db_user.organization_name == "My Org"
    
    db_service = (await session.exec(select(Service).where(Service.name == "API"))).first()
    assert db_service is not None
    assert db_service.current_status == ServiceStatus.OPERATIONAL
    
    db_incident = (await session.exec(select(Incident).where(Incident.title == "API Outage"))).first()
    assert db_incident is not None
    assert db_incident.status == IncidentStatus.INVESTIGATING
    
    db_link = (await session.exec(select(IncidentServiceLink))).first()
    assert db_link is not None
    assert db_link.incident_id == db_incident.id
    assert db_link.service_id == db_service.id
    
    db_sub = (await session.exec(select(Subscriber))).first()
    assert db_sub is not None
    assert db_sub.email == "sub@test.com"
