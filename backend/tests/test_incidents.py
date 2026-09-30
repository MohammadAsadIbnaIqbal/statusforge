import pytest
from httpx import AsyncClient
import sqlalchemy as sa
from sqlmodel import select
from tests.conftest import test_engine
from app.models.incident import Incident, IncidentStatus, IncidentImpact
from app.models.service import Service, ServiceStatus

async def register_user(client: AsyncClient, num: int):
    response = await client.post(
        "/register",
        json={"username": f"user{num}", "password": "password", "email": f"user{num}@example.com", "organization_name": f"Org {num}"}
    )
    return response.json()["access_token"]

async def create_service(client: AsyncClient, token: str, name: str):
    res = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": name})
    return res.json()["id"]

@pytest.mark.asyncio
async def test_create_valid_incident(client: AsyncClient):
    token = await register_user(client, 1)
    s_id = await create_service(client, token, "Web App")
    
    res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Database Outage",
            "impact": "CRITICAL",
            "service_ids": [s_id],
            "message": "We are investigating an issue with the DB."
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Database Outage"
    assert data["status"] == "INVESTIGATING"
    
    # Verify service status was updated
    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}"})
    assert s_res.json()["current_status"] == "MAJOR_OUTAGE"

@pytest.mark.asyncio
async def test_create_incident_unauth(client: AsyncClient):
    res = await client.post("/incidents", json={"title": "T", "impact": "MINOR", "service_ids": [1], "message": "M"})
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_create_incident_other_users_service(client: AsyncClient):
    token1 = await register_user(client, 1)
    token2 = await register_user(client, 2)
    s1_id = await create_service(client, token1, "Web App")
    
    res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token2}"},
        json={
            "title": "Hacking",
            "impact": "CRITICAL",
            "service_ids": [s1_id],
            "message": "M"
        }
    )
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_update_incident_lifecycle(client: AsyncClient):
    token = await register_user(client, 1)
    s_id = await create_service(client, token, "Web App")
    
    res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Outage", "impact": "MAJOR", "service_ids": [s_id], "message": "Investigating"}
    )
    inc_id = res.json()["id"]
    
    # Update to IDENTIFIED
    up1 = await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "IDENTIFIED", "message": "Found the issue"}
    )
    assert up1.status_code == 200
    assert up1.json()["status"] == "IDENTIFIED"
    assert up1.json()["resolved_at"] is None
    
    # Update to RESOLVED
    up2 = await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "RESOLVED", "message": "Fixed"}
    )
    assert up2.status_code == 200
    assert up2.json()["resolved_at"] is not None
    
    # Try updating again (should fail)
    up3 = await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "INVESTIGATING", "message": "Reopened"}
    )
    assert up3.status_code == 400

@pytest.mark.asyncio
async def test_service_status_logic(client: AsyncClient):
    token = await register_user(client, 1)
    s_id = await create_service(client, token, "API")
    
    # 1. MINOR incident -> DEGRADED
    inc1_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Slow network", "impact": "MINOR", "service_ids": [s_id], "message": "x"}
    )
    inc1_id = inc1_res.json()["id"]
    
    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}"})
    assert s_res.json()["current_status"] == "DEGRADED_PERFORMANCE"
    
    # 2. MAJOR incident -> PARTIAL_OUTAGE
    inc2_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "API broken", "impact": "MAJOR", "service_ids": [s_id], "message": "x"}
    )
    inc2_id = inc2_res.json()["id"]
    
    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}"})
    assert s_res.json()["current_status"] == "PARTIAL_OUTAGE"
    
    # 3. Resolve MAJOR incident -> DEGRADED (drops back to MINOR)
    await client.post(
        f"/incidents/{inc2_id}/updates",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "RESOLVED", "message": "Fixed API"}
    )
    
    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}"})
    assert s_res.json()["current_status"] == "DEGRADED_PERFORMANCE"
    
    # 4. Resolve MINOR incident -> OPERATIONAL
    await client.post(
        f"/incidents/{inc1_id}/updates",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "RESOLVED", "message": "Network restored"}
    )
    
    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}"})
    assert s_res.json()["current_status"] == "OPERATIONAL"

@pytest.mark.asyncio
async def test_incident_ownership(client: AsyncClient):
    token1 = await register_user(client, 1)
    token2 = await register_user(client, 2)
    s_id = await create_service(client, token1, "Web App")
    
    res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token1}"},
        json={"title": "Outage", "impact": "MAJOR", "service_ids": [s_id], "message": "Investigating"}
    )
    inc_id = res.json()["id"]
    
    # User 2 tries to update User 1's incident
    up = await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token2}"},
        json={"status": "RESOLVED", "message": "Fixed"}
    )
    assert up.status_code == 404

import pytest

@pytest.mark.asyncio

async def test_get_incidents_unauthenticated(client: AsyncClient):
    response = await client.get("/incidents")
    assert response.status_code == 401

async def test_get_incidents(client: AsyncClient):
    token = await register_user(client, 1)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/incidents", headers=headers)
    assert response.status_code == 200

async def test_get_incident_detail(client: AsyncClient):
    token = await register_user(client, 1)
    headers = {"Authorization": f"Bearer {token}"}
    s_id = await create_service(client, token, "Web App")
    
    inc_res = await client.post("/incidents", json={
        "title": "T1",
        "status": "INVESTIGATING",
        "impact": "MINOR",
        "service_ids": [s_id],
        "message": "M1"
    }, headers=headers)
    inc_id = inc_res.json()["id"]
    
    # Get detail
    detail_res = await client.get(f"/incidents/{inc_id}", headers=headers)
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == inc_id
    assert len(data["services"]) == 1
    assert data["services"][0]["id"] == s_id
    assert len(data["updates"]) == 1
    
    # Get list
    list_res = await client.get("/incidents", headers=headers)
    list_data = list_res.json()
    assert list_data["total"] >= 1

async def test_incident_isolation(client: AsyncClient):
    token1 = await register_user(client, 1)
    token2 = await register_user(client, 2)
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    s_id = await create_service(client, token1, "App")
    
    inc_res = await client.post("/incidents", json={
        "title": "T1",
        "status": "INVESTIGATING",
        "impact": "MINOR",
        "service_ids": [s_id],
        "message": "M1"
    }, headers=headers1)
    inc_id = inc_res.json()["id"]
    
    # User 2 tries to access user 1's incident
    res = await client.get(f"/incidents/{inc_id}", headers=headers2)
    assert res.status_code == 404
    
    # User 2 tries to list incidents, should be empty
    res_list = await client.get("/incidents", headers=headers2)
    assert res_list.json()["total"] == 0

async def test_get_nonexistent_incident(client: AsyncClient):
    token = await register_user(client, 1)
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get("/incidents/99999", headers=headers)
    assert res.status_code == 404

async def test_get_incidents_filtering_and_pagination(client: AsyncClient):
    token = await register_user(client, 1)
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get("/incidents?limit=1&offset=0&status=INVESTIGATING", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
