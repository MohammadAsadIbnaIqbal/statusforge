import pytest
from httpx import AsyncClient
from sqlmodel import select
import sqlalchemy as sa
from tests.conftest import test_engine

async def bootstrap_user(client: AsyncClient, num: int):
    response = await client.post(
        "/auth/bootstrap",
        json={"organization_name": f"Org {num}"},
        headers={"Authorization": f"Bearer mock-uid-{num}"}
    )
    # Return the org slug to use for subsequent requests
    me_resp = await client.get("/organizations", headers={"Authorization": f"Bearer mock-uid-{num}"})
    return f"mock-uid-{num}", me_resp.json()[0]["slug"], me_resp.json()[0]["id"]

@pytest.mark.asyncio
async def test_create_service(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)

    response = await client.post(
        "/services",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
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
    token1, slug1, _ = await bootstrap_user(client, 1)
    token2, slug2, _ = await bootstrap_user(client, 2)

    res1 = await client.post("/services", headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}, json={"name": "User 1 Service"})
    assert res1.status_code == 201
    s1_id = res1.json()["id"]

    res_list2 = await client.get("/services", headers={"Authorization": f"Bearer {token2}", "X-Organization-Slug": slug2})
    assert len(res_list2.json()) == 0

    res_list1 = await client.get("/services", headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1})
    assert len(res_list1.json()) == 1

    res_get2 = await client.get(f"/services/{s1_id}", headers={"Authorization": f"Bearer {token2}", "X-Organization-Slug": slug2})
    assert res_get2.status_code == 404

    res_get1 = await client.get(f"/services/{s1_id}", headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1})
    assert res_get1.status_code == 200

@pytest.mark.asyncio
async def test_update_service(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)
    res = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "Service A"})
    s_id = res.json()["id"]

    update_res = await client.patch(
        f"/services/{s_id}",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"name": "Service B", "display_order": 10, "current_status": "MAJOR_OUTAGE"}
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] == "Service B"
    assert data["display_order"] == 10
    assert data["current_status"] == "OPERATIONAL"

@pytest.mark.asyncio
async def test_delete_service(client: AsyncClient):
    token1, slug1, _ = await bootstrap_user(client, 1)
    token2, slug2, _ = await bootstrap_user(client, 2)

    res = await client.post("/services", headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}, json={"name": "To Delete"})
    s_id = res.json()["id"]

    del2 = await client.delete(f"/services/{s_id}", headers={"Authorization": f"Bearer {token2}", "X-Organization-Slug": slug2})
    assert del2.status_code == 404

    del1 = await client.delete(f"/services/{s_id}", headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1})
    assert del1.status_code == 204

    get1 = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1})
    assert get1.status_code == 404

@pytest.mark.asyncio
async def test_max_20_services(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)
    from app.routers.services import limiter as services_limiter

    for i in range(20):
        services_limiter.reset()
        res = await client.post(
            "/services",
            headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
            json={"name": f"Service {i}"}
        )
        assert res.status_code == 201

    services_limiter.reset()
    res21 = await client.post(
        "/services",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"name": "Service 21"}
    )
    assert res21.status_code == 409

@pytest.mark.asyncio
async def test_delete_blocked_by_incident(client: AsyncClient):
    token, slug, org_id = await bootstrap_user(client, 1)

    res = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "Critical DB"})
    assert res.status_code == 201
    s_id = res.json()["id"]

    async with test_engine.begin() as conn:
        await conn.execute(
            sa.text(f"INSERT INTO incident (title, status, impact, organization_id, created_at, updated_at) VALUES ('Outage', 'INVESTIGATING', 'CRITICAL', {org_id}, '2026-01-01', '2026-01-01')")
        )
        incident_id = (await conn.execute(sa.text("SELECT id FROM incident"))).fetchone()[0]
        await conn.execute(
            sa.text(f"INSERT INTO incident_services (incident_id, service_id) VALUES ({incident_id}, {s_id})")
        )

    del_res = await client.delete(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert del_res.status_code == 409

    async with test_engine.begin() as conn:
        await conn.execute(sa.text(f"UPDATE incident SET status='RESOLVED' WHERE id={incident_id}"))

    del_res2 = await client.delete(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert del_res2.status_code == 204

@pytest.mark.asyncio
async def test_list_ordering(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)

    res1 = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "S1"})
    await client.patch(f"/services/{res1.json()['id']}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"display_order": 2})

    res2 = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "S2"})
    await client.patch(f"/services/{res2.json()['id']}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"display_order": 1})

    res3 = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "S3"})
    await client.patch(f"/services/{res3.json()['id']}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"display_order": 1})

    res = await client.get("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    data = res.json()

    assert data[0]["name"] == "S2"
    assert data[1]["name"] == "S3"
    assert data[2]["name"] == "S1"
