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

@pytest.mark.asyncio
async def test_public_subscription_rate_limit(client: AsyncClient):
    from app.routers.public_status import limiter
    limiter.enabled = True
    limiter.reset()

    token, slug, _ = await bootstrap_user(client, 901)

    for i in range(5):
        res = await client.post(f"/status/{slug}/subscribe", json={"email": f"test{i}@example.com"})
        assert res.status_code == 201

    res_limit = await client.post(f"/status/{slug}/subscribe", json={"email": "test99@example.com"})
    assert res_limit.status_code == 429

    limiter.enabled = False
