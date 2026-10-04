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

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

# Mock Firebase token
MOCK_FIREBASE_UID = "test-uid-123"
MOCK_EMAIL = "test@example.com"
MOCK_NAME = "Test User"
MOCK_PICTURE = "https://example.com/pic.jpg"
MOCK_ORG_SLUG = "test-org"

async def mock_verify_firebase_token():
    return {
        "uid": MOCK_FIREBASE_UID,
        "email": MOCK_EMAIL,
        "name": MOCK_NAME,
        "picture": MOCK_PICTURE,
        "email_verified": True
    }

app.dependency_overrides[verify_firebase_token] = mock_verify_firebase_token

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
        firebase_uid=MOCK_FIREBASE_UID,
        email=MOCK_EMAIL,
        display_name=MOCK_NAME,
        photo_url=MOCK_PICTURE
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    
    org = Organization(
        name="Test Org",
        slug=MOCK_ORG_SLUG,
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
