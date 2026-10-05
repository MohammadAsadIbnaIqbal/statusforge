import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

async def bootstrap_user(client: AsyncClient, num: int):
    await client.post(
        "/auth/bootstrap",
        json={"organization_name": f"Org {num}"},
        headers={"Authorization": f"Bearer mock-uid-{num}"}
    )
    me_resp = await client.get("/organizations", headers={"Authorization": f"Bearer mock-uid-{num}"})
    return f"mock-uid-{num}", me_resp.json()[0]["slug"], me_resp.json()[0]["id"]

@pytest.mark.asyncio
async def test_incident_resolution_cache_invalidation(client: AsyncClient, monkeypatch):
    called_keys = []

    mock_redis = AsyncMock()
    async def mock_enqueue_job(job_name, *args, **kwargs):
        if job_name == "invalidate_cache":
            called_keys.append(args[0])

    mock_redis.enqueue_job = mock_enqueue_job

    async def mock_create_pool(*args, **kwargs):
        return mock_redis

    monkeypatch.setattr("app.services.incident_service.create_pool", mock_create_pool)

    token, slug, _ = await bootstrap_user(client, 1)

    s_res = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "API"})
    s_id = s_res.json()["id"]

    inc_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"title": "API Down", "impact": "CRITICAL", "service_ids": [s_id], "message": "Investigating"}
    )
    inc_id = inc_res.json()["id"]

    expected_key = f"statusforge:status:{slug}"
    assert expected_key in called_keys
    called_keys.clear()

    await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"status": "IDENTIFIED", "message": "Identified the issue"}
    )

    assert expected_key in called_keys
    called_keys.clear()

    await client.post(
        f"/incidents/{inc_id}/updates",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"status": "RESOLVED", "message": "Fixed"}
    )

    assert expected_key in called_keys
