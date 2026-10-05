import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_auth_missing_token(client: AsyncClient):
    response = await client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authentication credentials"

@pytest.mark.asyncio
async def test_auth_invalid_scheme(client: AsyncClient):
    response = await client.get("/auth/me", headers={"Authorization": "Basic something"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication scheme"

@pytest.mark.asyncio
async def test_bootstrap_new_user(client: AsyncClient):
    response = await client.post(
        "/auth/bootstrap",
        json={"organization_name": "Test Organization"},
        headers={"Authorization": "Bearer mock-uid-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "1@example.com"
    assert "id" in data

    me_resp = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer mock-uid-1"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "1@example.com"

@pytest.mark.asyncio
async def test_bootstrap_idempotent(client: AsyncClient):
    r1 = await client.post(
        "/auth/bootstrap",
        json={"organization_name": "Test Organization"},
        headers={"Authorization": "Bearer mock-uid-2"}
    )
    assert r1.status_code == 200

    r2 = await client.post(
        "/auth/bootstrap",
        json={"organization_name": "Another Organization"},
        headers={"Authorization": "Bearer mock-uid-2"}
    )
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]

@pytest.mark.asyncio
async def test_bootstrap_slug_collision(client: AsyncClient):
    r1 = await client.post(
        "/auth/bootstrap",
        json={"organization_name": "My SaaS"},
        headers={"Authorization": "Bearer mock-uid-3"}
    )
    assert r1.status_code == 200

    r2 = await client.post(
        "/auth/bootstrap",
        json={"organization_name": "My SaaS!"},
        headers={"Authorization": "Bearer mock-uid-4"}
    )
    assert r2.status_code == 200
