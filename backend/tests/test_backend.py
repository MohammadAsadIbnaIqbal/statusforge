import pytest
from httpx import AsyncClient
from typing import Dict, Any

@pytest.mark.asyncio
async def test_bootstrap(client: AsyncClient):
    response = await client.post(
        "/auth/bootstrap",
        json={"organization_name": "Test Organization"},
        headers={"Authorization": "Bearer mock-token"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_organizations(client: AsyncClient, setup_test_user: Dict[str, Any]):
    response = await client.get("/organizations", headers={"Authorization": "Bearer mock-token"})
    assert response.status_code == 200
    orgs = response.json()
    assert len(orgs) > 0
    org = orgs[0]
    assert org["name"] == "Test Org"

@pytest.mark.asyncio
async def test_create_service(client: AsyncClient, setup_test_user: Dict[str, Any]):
    response = await client.post(
        "/services",
        json={"name": "Web App", "description": "Main application frontend"},
        headers={"Authorization": "Bearer mock-token", "X-Organization-Slug": "test-org"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Web App"
    assert data["organization_id"] is not None

@pytest.mark.asyncio
async def test_create_incident(client: AsyncClient, setup_test_user: Dict[str, Any]):
    # Create a service first
    await client.post(
        "/services",
        json={"name": "Web App"},
        headers={"Authorization": "Bearer mock-token", "X-Organization-Slug": "test-org"}
    )
    
    srv_resp = await client.get("/services", headers={"Authorization": "Bearer mock-token", "X-Organization-Slug": "test-org"})
    services = srv_resp.json()
    service_id = services[0]["id"]
    
    response = await client.post(
        "/incidents",
        json={
            "title": "Outage",
            "impact": "CRITICAL",
            "status": "INVESTIGATING",
            "message": "We are looking into this.",
            "service_ids": [service_id]
        },
        headers={"Authorization": "Bearer mock-token", "X-Organization-Slug": "test-org"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Outage"
    
@pytest.mark.asyncio
async def test_public_status(client: AsyncClient, setup_test_user: Dict[str, Any]):
    response = await client.get("/status/test-org")
    assert response.status_code == 200
    data = response.json()
    assert data["organization"]["slug"] == "test-org"
