import pytest
from httpx import AsyncClient
import sqlalchemy as sa
import sqlalchemy as sa
from sqlmodel import select
from tests.conftest import test_engine
from app.models.service import Service, ServiceStatus
from app.models.incident import Incident, IncidentStatus, IncidentServiceLink

async def register_user(client: AsyncClient, num: int):
    response = await client.post(
        "/register",
        json={"username": f"user{num}", "password": "password", "email": f"user{num}@example.com", "organization_name": f"Org {num}"}
    )
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_create_service(client: AsyncClient):
    token = await register_user(client, 1)
    
    response = await client.post(
        "/services",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "API Server", "description": "Core API"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Server"
    assert data["description"] == "Core API"
    assert data["current_status"] == "OPERATIONAL"

@pytest.mark.asyncio
async def test_create_service_unauthorized(client: AsyncClient):
    response = await client.post(
        "/services",
        json={"name": "API Server"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_list_and_ownership(client: AsyncClient):
    token1 = await register_user(client, 1)
    token2 = await register_user(client, 2)
    
    # User 1 creates a service
    res1 = await client.post("/services", headers={"Authorization": f"Bearer {token1}"}, json={"name": "User 1 Service"})
    assert res1.status_code == 201
    s1_id = res1.json()["id"]

    # User 2 lists services (should be empty)
    res_list2 = await client.get("/services", headers={"Authorization": f"Bearer {token2}"})
    assert len(res_list2.json()) == 0

    # User 1 lists services (should have 1)
    res_list1 = await client.get("/services", headers={"Authorization": f"Bearer {token1}"})
    assert len(res_list1.json()) == 1

    # User 2 attempts to get User 1's service
    res_get2 = await client.get(f"/services/{s1_id}", headers={"Authorization": f"Bearer {token2}"})
    assert res_get2.status_code == 404
    
    # User 1 gets own service
    res_get1 = await client.get(f"/services/{s1_id}", headers={"Authorization": f"Bearer {token1}"})
    assert res_get1.status_code == 200

@pytest.mark.asyncio
async def test_update_service(client: AsyncClient):
    token = await register_user(client, 1)
    res = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "Service A"})
    s_id = res.json()["id"]
    
    # Valid update
    update_res = await client.patch(
        f"/services/{s_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Service B", "display_order": 10, "current_status": "MAJOR_OUTAGE"}
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] == "Service B"
    assert data["display_order"] == 10
    assert data["current_status"] == "OPERATIONAL" # Because client cannot update current_status!

@pytest.mark.asyncio
async def test_delete_service(client: AsyncClient):
    token1 = await register_user(client, 1)
    token2 = await register_user(client, 2)
    
    res = await client.post("/services", headers={"Authorization": f"Bearer {token1}"}, json={"name": "To Delete"})
    s_id = res.json()["id"]
    
    # User 2 attempts to delete user 1's service
    del2 = await client.delete(f"/services/{s_id}", headers={"Authorization": f"Bearer {token2}"})
    assert del2.status_code == 404
    
    # User 1 deletes their own
    del1 = await client.delete(f"/services/{s_id}", headers={"Authorization": f"Bearer {token1}"})
    assert del1.status_code == 204
    
    # Verify deleted
    get1 = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token1}"})
    assert get1.status_code == 404

@pytest.mark.asyncio
async def test_max_20_services(client: AsyncClient):
    token = await register_user(client, 1)
    
    from app.routers.services import limiter as services_limiter
    
    for i in range(20):
        # Reset limiter to allow this test to create 20 services sequentially
        services_limiter.reset()
        res = await client.post(
            "/services",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": f"Service {i}"}
        )
        assert res.status_code == 201
        
    services_limiter.reset()
    res21 = await client.post(
        "/services",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Service 21"}
    )
    assert res21.status_code == 409
    assert "Maximum number of services" in res21.json()["detail"]

@pytest.mark.asyncio
async def test_delete_blocked_by_incident(client: AsyncClient):
    token = await register_user(client, 1)
    
    # Create service
    res = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "Critical DB"})
    assert res.status_code == 201
    s_id = res.json()["id"]
    owner_id = res.json()["owner_id"]
    
    # Manually create incident and link it
    async with test_engine.begin() as conn:
        # We use synchronous-like insertion here for the test via SQLAlchemy
        await conn.execute(
            sa.text(f"INSERT INTO incident (title, status, impact, owner_id, created_at, updated_at) VALUES ('Outage', 'INVESTIGATING', 'CRITICAL', {owner_id}, '2026-01-01', '2026-01-01')")
        )
        # Fetch the incident ID (SQLite)
        incident_id = (await conn.execute(sa.text("SELECT id FROM incident"))).fetchone()[0]
        
        await conn.execute(
            sa.text(f"INSERT INTO incident_services (incident_id, service_id) VALUES ({incident_id}, {s_id})")
        )
        
    # Try to delete
    del_res = await client.delete(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 409
    assert "active incident" in del_res.json()["detail"]
    
    # Resolve the incident
    async with test_engine.begin() as conn:
        await conn.execute(sa.text(f"UPDATE incident SET status='RESOLVED' WHERE id={incident_id}"))
        
    # Try to delete again
    del_res2 = await client.delete(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res2.status_code == 204

@pytest.mark.asyncio
async def test_list_ordering(client: AsyncClient):
    token = await register_user(client, 1)
    
    # Create unordered services
    res1 = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "S1"})
    assert res1.status_code == 201
    await client.patch(f"/services/{res1.json()['id']}", headers={"Authorization": f"Bearer {token}"}, json={"display_order": 2})
    
    res2 = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "S2"})
    assert res2.status_code == 201
    await client.patch(f"/services/{res2.json()['id']}", headers={"Authorization": f"Bearer {token}"}, json={"display_order": 1})
    
    res3 = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "S3"})
    assert res3.status_code == 201
    await client.patch(f"/services/{res3.json()['id']}", headers={"Authorization": f"Bearer {token}"}, json={"display_order": 1})
    
    res = await client.get("/services", headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    
    # S2 and S3 have order 1, S1 has order 2. 
    # Between S2 and S3, S2 was created first (so S2 is before S3).
    assert data[0]["name"] == "S2"
    assert data[1]["name"] == "S3"
    assert data[2]["name"] == "S1"
