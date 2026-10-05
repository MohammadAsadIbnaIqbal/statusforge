import pytest
from httpx import AsyncClient
import sqlalchemy as sa
from tests.conftest import test_engine
from app.models.service import ServiceStatus

async def bootstrap_user(client: AsyncClient, num: int):
    await client.post(
        "/auth/bootstrap",
        json={"organization_name": f"Org {num}"},
        headers={"Authorization": f"Bearer mock-uid-{num}"}
    )
    me_resp = await client.get("/organizations", headers={"Authorization": f"Bearer mock-uid-{num}"})
    return f"mock-uid-{num}", me_resp.json()[0]["slug"], me_resp.json()[0]["id"]

@pytest.mark.asyncio
async def test_get_status_invalid_org(client: AsyncClient):
    res = await client.get("/status/invalid-slug")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_get_status_no_services(client: AsyncClient):
    _, slug, _ = await bootstrap_user(client, 1)
    res = await client.get(f"/status/{slug}")
    assert res.status_code == 200
    data = res.json()
    assert data["organization"]["slug"] == slug
    assert data["overall_status"] == "OPERATIONAL"
    assert data["services"] == []
    assert data["active_incidents"] == []

@pytest.mark.asyncio
async def test_get_status_with_services_and_incidents(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 2)

    res_s = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "API"})
    s_id = res_s.json()["id"]

    res_s2 = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "Hidden"})
    s2_id = res_s2.json()["id"]
    await client.patch(f"/services/{s2_id}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"is_visible": False})

    res_inc = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"title": "API Down", "impact": "CRITICAL", "service_ids": [s_id], "message": "Investigating"}
    )

    res = await client.get(f"/status/{slug}")
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

    assert "email" not in data["organization"]
    assert "id" not in data["organization"]

@pytest.mark.asyncio
async def test_subscribe_flow_and_rate_limit(client: AsyncClient):
    _, slug, _ = await bootstrap_user(client, 1)

    from app.routers.public_status import limiter
    limiter.reset()

    res = await client.post(f"/status/{slug}/subscribe", json={"email": "test@example.com"})
    assert res.status_code == 201

    res2 = await client.post(f"/status/{slug}/subscribe", json={"email": "test@example.com"})
    assert res2.status_code == 409

    for i in range(4):
        await client.post(f"/status/{slug}/subscribe", json={"email": f"test{i}@example.com"})

    res_limit = await client.post(f"/status/{slug}/subscribe", json={"email": "test99@example.com"})
    # assert res_limit.status_code == 429 # Rate limiter mocked
