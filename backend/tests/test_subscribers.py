import pytest
from httpx import AsyncClient
import sqlalchemy as sa
from tests.conftest import test_engine
from datetime import datetime, timezone, timedelta
from app.models.subscriber import Subscriber

async def bootstrap_user(client: AsyncClient, num: int):
    await client.post(
        "/auth/bootstrap",
        json={"organization_name": f"Org {num}"},
        headers={"Authorization": f"Bearer mock-uid-{num}"}
    )
    me_resp = await client.get("/organizations", headers={"Authorization": f"Bearer mock-uid-{num}"})
    return f"mock-uid-{num}", me_resp.json()[0]["slug"], me_resp.json()[0]["id"]

@pytest.mark.asyncio
async def test_subscriber_lifecycle(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)

    await client.post(f"/status/{slug}/subscribe", json={"email": "sub1@example.com"})

    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token, unsubscribe_token FROM subscriber WHERE email='sub1@example.com'"))).fetchone()
        conf_token = row[0]
        unsub_token = row[1]

    list_res = await client.get("/subscribers", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["email"] == "sub1@example.com"
    assert list_res.json()[0]["is_confirmed"] is False

    conf_res = await client.get(f"/subscribers/confirm/{conf_token}")
    assert conf_res.status_code == 200

    list_res = await client.get("/subscribers", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert list_res.json()[0]["is_confirmed"] is True

    conf_res2 = await client.get(f"/subscribers/confirm/{conf_token}")
    assert conf_res2.status_code == 404

    unsub_res = await client.get(f"/subscribers/unsubscribe/{unsub_token}")
    assert unsub_res.status_code == 200

    list_res = await client.get("/subscribers", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert len(list_res.json()) == 0

@pytest.mark.asyncio
async def test_expired_token(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 1)

    await client.post(f"/status/{slug}/subscribe", json={"email": "expired@example.com"})

    async with test_engine.begin() as conn:
        past = datetime.now(timezone.utc) - timedelta(days=2)
        past_str = past.strftime('%Y-%m-%d %H:%M:%S')
        await conn.execute(sa.text(f"UPDATE subscriber SET confirmation_token_expires_at='{past_str}' WHERE email='expired@example.com'"))
        row = (await conn.execute(sa.text("SELECT confirmation_token FROM subscriber WHERE email='expired@example.com'"))).fetchone()
        conf_token = row[0]

    res = await client.get(f"/subscribers/confirm/{conf_token}")
    assert res.status_code == 410

    res_re = await client.post(f"/status/{slug}/subscribe", json={"email": "expired@example.com"})
    assert res_re.status_code == 201

@pytest.mark.asyncio
async def test_subscriber_isolation(client: AsyncClient):
    token1, slug1, _ = await bootstrap_user(client, 1)
    token2, slug2, _ = await bootstrap_user(client, 2)

    await client.post(f"/status/{slug1}/subscribe", json={"email": "sub@example.com"})

    res = await client.get("/subscribers", headers={"Authorization": f"Bearer {token2}", "X-Organization-Slug": slug2})
    assert len(res.json()) == 0

@pytest.mark.asyncio
async def test_invalid_unsubscribe_token(client: AsyncClient):
    res = await client.get("/subscribers/unsubscribe/invalid_token_12345")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_duplicate_active_subscription(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 3)
    res1 = await client.post(f"/status/{slug}/subscribe", json={"email": "dup@example.com"})
    assert res1.status_code == 201

    res2 = await client.post(f"/status/{slug}/subscribe", json={"email": "dup@example.com"})
    assert res2.status_code == 409
    assert res2.json()["detail"] == "Email already subscribed"

    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token FROM subscriber WHERE email='dup@example.com'"))).fetchone()
        conf_token = row[0]
    await client.get(f"/subscribers/confirm/{conf_token}")

    res3 = await client.post(f"/status/{slug}/subscribe", json={"email": "dup@example.com"})
    assert res3.status_code == 409
    assert res3.json()["detail"] == "Email already subscribed"

@pytest.mark.asyncio
async def test_resubscribe_after_unsubscribe(client: AsyncClient):
    token, slug, _ = await bootstrap_user(client, 4)
    await client.post(f"/status/{slug}/subscribe", json={"email": "resub@example.com"})

    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token, unsubscribe_token FROM subscriber WHERE email='resub@example.com'"))).fetchone()
        conf_token = row[0]
        unsub_token = row[1]

    await client.get(f"/subscribers/confirm/{conf_token}")
    await client.get(f"/subscribers/unsubscribe/{unsub_token}")

    list_res = await client.get("/subscribers", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert len(list_res.json()) == 0

    res2 = await client.post(f"/status/{slug}/subscribe", json={"email": "resub@example.com"})
    assert res2.status_code == 201

    list_res2 = await client.get("/subscribers", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug})
    assert len(list_res2.json()) == 1
    assert list_res2.json()[0]["is_confirmed"] is False
