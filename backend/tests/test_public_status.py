import pytest
from httpx import AsyncClient
import sqlalchemy as sa
from tests.conftest import test_engine
from app.models.service import ServiceStatus

async def register_user(client: AsyncClient, num: int):
    response = await client.post(
        "/register",
        json={"username": f"user{num}", "password": "password", "email": f"user{num}@example.com", "organization_name": f"Org {num}"}
    )
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_get_status_invalid_org(client: AsyncClient):
    res = await client.get("/status/invalid-slug")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_get_status_no_services(client: AsyncClient):
    await register_user(client, 1)
    res = await client.get("/status/org-1")
    assert res.status_code == 200
    data = res.json()
    assert data["organization"]["slug"] == "org-1"
    assert data["overall_status"] == "OPERATIONAL"
    assert data["services"] == []
    assert data["active_incidents"] == []

@pytest.mark.asyncio
async def test_get_status_with_services_and_incidents(client: AsyncClient):
    token = await register_user(client, 1)
    
    # 1. Create a service
    res_s = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "API"})
    s_id = res_s.json()["id"]
    
    # Create invisible service
    res_s2 = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "Hidden"})
    s2_id = res_s2.json()["id"]
    await client.patch(f"/services/{s2_id}", headers={"Authorization": f"Bearer {token}"}, json={"is_visible": False})
    
    # 2. Create incident
    res_inc = await client.post(
        "/incidents", 
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "API Down", "impact": "CRITICAL", "service_ids": [s_id], "message": "Investigating"}
    )
    
    # 3. Check public page
    res = await client.get("/status/org-1")
    assert res.status_code == 200
    data = res.json()
    
    assert data["overall_status"] == "MAJOR_OUTAGE"
    assert len(data["services"]) == 1
    assert data["services"][0]["name"] == "API"
    assert data["services"][0]["status"] == "MAJOR_OUTAGE"
    
    assert len(data["active_incidents"]) == 1
    assert data["active_incidents"][0]["title"] == "API Down"
    assert len(data["active_incidents"][0]["updates"]) == 1
    assert data["active_incidents"][0]["updates"][0]["message"] == "Investigating"

    # Make sure we don't leak user ID or email
    assert "email" not in data["organization"]
    assert "id" not in data["organization"]

@pytest.mark.asyncio
async def test_subscribe_flow_and_rate_limit(client: AsyncClient):
    await register_user(client, 1)
    
    # Test valid subscribe
    res = await client.post("/status/org-1/subscribe", json={"email": "test@example.com"})
    assert res.status_code == 201
    
    # Duplicate fails with 409
    res2 = await client.post("/status/org-1/subscribe", json={"email": "test@example.com"})
    assert res2.status_code == 409
    
    # Check rate limit (5/minute)
    for i in range(4):
        # We need unique emails, but the rate limit is per IP
        await client.post(
            "/status/org-1/subscribe", 
            json={"email": f"test{i}@example.com"}
        )
        
    res_limit = await client.post("/status/org-1/subscribe", json={"email": "test99@example.com"})
    assert res_limit.status_code == 429
