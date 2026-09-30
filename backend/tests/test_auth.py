import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post(
        "/register",
        json={
            "username": "testuser", 
            "password": "password123", 
            "email": "test@example.com", 
            "organization_name": "Test Org"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["organization_name"] == "Test Org"
    assert data["organization_slug"] == "test-org"
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "id" in data
    assert "password" not in data

@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    await client.post(
        "/register",
        json={"username": "dupuser", "password": "password123", "email": "dup1@example.com", "organization_name": "Org 1"}
    )
    response = await client.post(
        "/register",
        json={"username": "dupuser", "password": "password123", "email": "dup2@example.com", "organization_name": "Org 2"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Username already taken"

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post(
        "/register",
        json={"username": "dupemail1", "password": "password123", "email": "dup@example.com", "organization_name": "Org 1"}
    )
    response = await client.post(
        "/register",
        json={"username": "dupemail2", "password": "password123", "email": "dup@example.com", "organization_name": "Org 2"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"

@pytest.mark.asyncio
async def test_register_slug_collision(client: AsyncClient):
    # First user
    response1 = await client.post(
        "/register",
        json={"username": "sluguser1", "password": "password123", "email": "slug1@example.com", "organization_name": "My SaaS"}
    )
    assert response1.status_code == 201
    assert response1.json()["organization_slug"] == "my-saas"

    # Second user with same org name
    response2 = await client.post(
        "/register",
        json={"username": "sluguser2", "password": "password123", "email": "slug2@example.com", "organization_name": "My SaaS!"}
    )
    assert response2.status_code == 201
    assert response2.json()["organization_slug"] == "my-saas-2"

@pytest.mark.asyncio
async def test_register_invalid_organization_name(client: AsyncClient):
    response = await client.post(
        "/register",
        json={"username": "invalidorg", "password": "password123", "email": "invalidorg@example.com", "organization_name": "A" * 101}
    )
    assert response.status_code == 422 # Pydantic validation error for max_length

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    await client.post(
        "/register",
        json={"username": "loginuser", "password": "password123", "email": "login@example.com", "organization_name": "Login Org"}
    )

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

@pytest.mark.asyncio
async def test_auth_me(client: AsyncClient):
    register_response = await client.post(
        "/register",
        json={"username": "meuser", "password": "password123", "email": "me@example.com", "organization_name": "Me Org"}
    )
    token = register_response.json()["access_token"]
    
    response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "meuser"
    assert data["organization_slug"] == "me-org"