from collections.abc import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_session
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, Role
from app.core.dependencies import verify_firebase_token
from fastapi import Request, HTTPException, status

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

async def mock_verify_firebase_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_val = parts[1]
    if token_val.startswith("mock-uid-"):
        uid = token_val.split("mock-uid-")[1]
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "uid": uid,
        "email": f"{uid}@example.com",
        "name": f"User {uid}",
        "picture": "https://example.com/pic.jpg",
        "email_verified": True
    }

app.dependency_overrides[verify_firebase_token] = mock_verify_firebase_token

@pytest.fixture(autouse=True)
def disable_rate_limit():
    from app.routers.services import limiter as services_limiter
    from app.routers.public_status import limiter as public_limiter

    services_limiter.enabled = False
    public_limiter.enabled = False
    yield
    services_limiter.enabled = True
    public_limiter.enabled = True

@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture
async def setup_test_user(test_session: AsyncSession):
    user = User(
        firebase_uid="test-uid-123",
        email="test-uid-123@example.com",
        display_name="User test-uid-123",
        photo_url="https://example.com/pic.jpg"
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    org = Organization(
        name="Test Org",
        slug="test-org",
        created_by=user.id
    )
    test_session.add(org)
    await test_session.commit()
    await test_session.refresh(org)

    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=Role.OWNER
    )
    test_session.add(membership)
    await test_session.commit()

    return {"user": user, "org": org}

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
