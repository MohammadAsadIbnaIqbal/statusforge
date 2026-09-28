import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post(
        "/register",
        json={"username": "testuser", "password": "password123", "email": "test@example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data
    assert "password" not in data  # Ensure password is never exposed!

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    # 1. Register first
    await client.post(
        "/register",
        json={"username": "loginuser", "password": "password123"}
    )

    # 2. Log in
    response = await client.post(
        "/login",
        data={"username": "loginuser", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_protected_route_unauthorized(client: AsyncClient):
    response = await client.get("/users/me")
    assert response.status_code == 401