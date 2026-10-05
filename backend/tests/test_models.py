import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, Role
from app.models.service import Service, ServiceStatus
from app.models.incident import Incident, IncidentStatus, IncidentImpact, IncidentServiceLink
from app.models.subscriber import Subscriber

@pytest.mark.asyncio
async def test_create_and_query_models(client, setup_db):
    from app.core.database import get_session
    from app.main import app

    session_generator = app.dependency_overrides[get_session]()
    session: AsyncSession = await session_generator.__anext__()

    user = User(
        firebase_uid="uid-123",
        email="owner@org.com",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    org = Organization(
        name="My Org",
        slug="my-org",
        created_by=user.id
    )
    session.add(org)
    await session.commit()
    await session.refresh(org)

    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=Role.OWNER
    )
    session.add(membership)
    await session.commit()

    service = Service(
        name="API",
        description="Core API",
        organization_id=org.id
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)

    incident = Incident(
        title="API Outage",
        impact=IncidentImpact.CRITICAL,
        organization_id=org.id
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)

    link = IncidentServiceLink(incident_id=incident.id, service_id=service.id)
    session.add(link)
    await session.commit()

    subscriber = Subscriber(
        email="sub@test.com",
        organization_id=org.id,
        unsubscribe_token="token123"
    )
    session.add(subscriber)
    await session.commit()
    await session.refresh(subscriber)

    db_user = (await session.exec(select(User).where(User.firebase_uid == "uid-123"))).first()
    assert db_user is not None

    db_org = (await session.exec(select(Organization).where(Organization.slug == "my-org"))).first()
    assert db_org is not None

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
