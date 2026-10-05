import pytest
from httpx import AsyncClient

async def bootstrap_user(client: AsyncClient, num: int):
    await client.post(
        "/auth/bootstrap",
        json={"organization_name": f"Org {num}"},
        headers={"Authorization": f"Bearer mock-uid-{num}"}
    )
    me_resp = await client.get("/organizations", headers={"Authorization": f"Bearer mock-uid-{num}"})
    return f"mock-uid-{num}", me_resp.json()[0]["slug"], me_resp.json()[0]["id"]

async def create_service(client: AsyncClient, token: str, slug: str, name: str):
    res = await client.post(
        "/services",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"name": name}
    )
    return res.json()["id"]

@pytest.mark.asyncio
async def test_create_valid_incident(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)
    s_id = await create_service(client, token, slug, "Web App")

    response = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={
            "title": "Major Outage",
            "impact": "MAJOR",
            "status": "INVESTIGATING",
            "message": "We are looking into this.",
            "service_ids": [s_id]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Major Outage"
    assert data["impact"] == "MAJOR"
    assert data["status"] == "INVESTIGATING"

    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert s_res.json()["current_status"] == "PARTIAL_OUTAGE"

@pytest.mark.asyncio
async def test_create_incident_unauth(client: AsyncClient):
    res = await client.post("/incidents", json={"title": "T", "impact": "MINOR", "service_ids": [1], "message": "M"})
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_create_incident_other_users_service(client: AsyncClient):
    token1, slug1, _ = await bootstrap_user(client, 1)
    token2, slug2, _ = await bootstrap_user(client, 2)
    s1_id = await create_service(client, token1, slug1, "Web App")

    res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token2}", "X-Organization-Slug": slug2},
        json={"title": "Hacking", "impact": "CRITICAL", "service_ids": [s1_id], "message": "M"}
    )
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_update_incident_lifecycle(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)
    s_id = await create_service(client, token, slug, "Web App")

    res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"title": "Outage", "impact": "MAJOR", "service_ids": [s_id], "message": "Investigating"}
    )
    inc_id = res.json()["id"]

    up1 = await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"status": "IDENTIFIED", "message": "Found the issue"}
    )
    assert up1.status_code == 200
    assert up1.json()["status"] == "IDENTIFIED"
    assert up1.json()["resolved_at"] is None

    up2 = await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"status": "RESOLVED", "message": "Fixed"}
    )
    assert up2.status_code == 200
    assert up2.json()["resolved_at"] is not None

    up3 = await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"status": "INVESTIGATING", "message": "Reopened"}
    )
    assert up3.status_code == 400

@pytest.mark.asyncio
async def test_service_status_logic(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)
    s_id = await create_service(client, token, slug, "API")

    inc1_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"title": "Slow network", "impact": "MINOR", "service_ids": [s_id], "message": "x"}
    )
    inc1_id = inc1_res.json()["id"]

    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert s_res.json()["current_status"] == "DEGRADED_PERFORMANCE"

    inc2_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"title": "API broken", "impact": "MAJOR", "service_ids": [s_id], "message": "x"}
    )
    inc2_id = inc2_res.json()["id"]

    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert s_res.json()["current_status"] == "PARTIAL_OUTAGE"

    await client.post(
        f"/incidents/{inc2_id}/updates",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"status": "RESOLVED", "message": "Fixed API"}
    )

    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert s_res.json()["current_status"] == "DEGRADED_PERFORMANCE"

    await client.post(
        f"/incidents/{inc1_id}/updates",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"status": "RESOLVED", "message": "Network restored"}
    )

    s_res = await client.get(f"/services/{s_id}", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert s_res.json()["current_status"] == "OPERATIONAL"

@pytest.mark.asyncio
async def test_incident_ownership(client: AsyncClient):
    token1, slug1, _ = await bootstrap_user(client, 1)
    token2, slug2, _ = await bootstrap_user(client, 2)
    s_id = await create_service(client, token1, slug1, "Web App")

    res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1},
        json={"title": "Outage", "impact": "MAJOR", "service_ids": [s_id], "message": "Investigating"}
    )
    inc_id = res.json()["id"]

    up = await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token2}", "X-Organization-Slug": slug2},
        json={"status": "RESOLVED", "message": "Fixed"}
    )
    assert up.status_code == 404

@pytest.mark.asyncio
async def test_get_incidents_unauthenticated(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 99)
    response = await client.get("/incidents", headers={"X-Organization-Slug": slug})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_incidents(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}
    response = await client.get("/incidents", headers=headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_incident_detail(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}
    s_id = await create_service(client, token, slug, "Web App")

    inc_res = await client.post("/incidents", json={
        "title": "T1",
        "status": "INVESTIGATING",
        "impact": "MINOR",
        "service_ids": [s_id],
        "message": "M1"
    }, headers=headers)
    inc_id = inc_res.json()["id"]

    detail_res = await client.get(f"/incidents/{inc_id}", headers=headers)
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == inc_id
    assert len(data["services"]) == 1
    assert data["services"][0]["id"] == s_id
    assert len(data["updates"]) == 1

    list_res = await client.get("/incidents", headers=headers)
    list_data = list_res.json()
    assert list_data["total"] >= 1

@pytest.mark.asyncio
async def test_incident_isolation(client: AsyncClient):
    token1, slug1, _ = await bootstrap_user(client, 1)
    token2, slug2, _ = await bootstrap_user(client, 2)
    headers1 = {"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    headers2 = {"Authorization": f"Bearer {token2}", "X-Organization-Slug": slug2}

    s_id = await create_service(client, token1, slug1, "App")

    inc_res = await client.post("/incidents", json={
        "title": "T1",
        "status": "INVESTIGATING",
        "impact": "MINOR",
        "service_ids": [s_id],
        "message": "M1"
    }, headers=headers1)
    inc_id = inc_res.json()["id"]

    res = await client.get(f"/incidents/{inc_id}", headers=headers2)
    assert res.status_code == 404

    res_list = await client.get("/incidents", headers=headers2)
    assert res_list.json()["total"] == 0

@pytest.mark.asyncio
async def test_get_nonexistent_incident(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}
    res = await client.get("/incidents/99999", headers=headers)
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_get_incidents_filtering_and_pagination(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}
    res = await client.get("/incidents?limit=1&offset=0&status=INVESTIGATING", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
