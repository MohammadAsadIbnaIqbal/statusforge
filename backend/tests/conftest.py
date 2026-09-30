from collections.abc import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_session
from app.models import *

# Use an in-memory SQLite database or test PostgreSQL database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

# Override the database session dependency for tests
async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

# Swap app's real session dependency with test database session
app.dependency_overrides[get_session] = override_get_session

from app.routers.auth import limiter as auth_limiter
from app.routers.services import limiter as services_limiter
from app.routers.public_status import limiter as public_limiter
from app.main import limiter as main_limiter

@pytest.fixture(autouse=True)
async def setup_db():
    """Create fresh tables before each test and drop them after."""
    # Ensure memory storage is cleared before every test
    auth_limiter.reset()
    services_limiter.reset()
    public_limiter.reset()
    main_limiter.reset()
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for making API requests in tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac