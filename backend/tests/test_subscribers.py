import pytest
from httpx import AsyncClient
import sqlalchemy as sa
from tests.conftest import test_engine
from datetime import datetime, timezone, timedelta
from app.models.subscriber import Subscriber

async def register_user(client: AsyncClient, num: int):
    response = await client.post(
        "/register",
        json={"username": f"user{num}", "password": "password", "email": f"user{num}@example.com", "organization_name": f"Org {num}"}
    )
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_subscriber_lifecycle(client: AsyncClient):
    token = await register_user(client, 1)
    
    # 1. Subscribe
    await client.post("/status/org-1/subscribe", json={"email": "sub1@example.com"})
    
    # 2. Get tokens directly from DB since emails are mocked
    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token, unsubscribe_token FROM subscriber WHERE email='sub1@example.com'"))).fetchone()
        conf_token = row[0]
        unsub_token = row[1]
        
    # 3. List subscribers (admin)
    list_res = await client.get("/subscribers", headers={"Authorization": f"Bearer {token}"})
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["email"] == "sub1@example.com"
    assert list_res.json()[0]["is_confirmed"] is False
    
    # 4. Confirm
    conf_res = await client.get(f"/subscribers/confirm/{conf_token}")
    assert conf_res.status_code == 200
    
    # Verify DB update
    list_res = await client.get("/subscribers", headers={"Authorization": f"Bearer {token}"})
    assert list_res.json()[0]["is_confirmed"] is True
    
    # Confirming again fails (token was deleted/set to NULL)
    conf_res2 = await client.get(f"/subscribers/confirm/{conf_token}")
    assert conf_res2.status_code == 404
    
    # 5. Unsubscribe
    unsub_res = await client.get(f"/subscribers/unsubscribe/{unsub_token}")
    assert unsub_res.status_code == 200
    
    # Verify DB empty
    list_res = await client.get("/subscribers", headers={"Authorization": f"Bearer {token}"})
    assert len(list_res.json()) == 0

@pytest.mark.asyncio
async def test_expired_token(client: AsyncClient):
    await register_user(client, 1)
    
    await client.post("/status/org-1/subscribe", json={"email": "expired@example.com"})
    
    # Manually expire the token
    async with test_engine.begin() as conn:
        past = datetime.now(timezone.utc) - timedelta(days=2)
        past_str = past.strftime('%Y-%m-%d %H:%M:%S')
        await conn.execute(sa.text(f"UPDATE subscriber SET confirmation_token_expires_at='{past_str}' WHERE email='expired@example.com'"))
        row = (await conn.execute(sa.text("SELECT confirmation_token FROM subscriber WHERE email='expired@example.com'"))).fetchone()
        conf_token = row[0]
        
    res = await client.get(f"/subscribers/confirm/{conf_token}")
    assert res.status_code == 410
    
    # Subscribing again with the same email should succeed and replace the old one
    res_re = await client.post("/status/org-1/subscribe", json={"email": "expired@example.com"})
    assert res_re.status_code == 201

@pytest.mark.asyncio
async def test_subscriber_isolation(client: AsyncClient):
    token1 = await register_user(client, 1)
    token2 = await register_user(client, 2)
    
    await client.post("/status/org-1/subscribe", json={"email": "sub@example.com"})
    
    # User 2 lists subscribers
    res = await client.get("/subscribers", headers={"Authorization": f"Bearer {token2}"})
    assert len(res.json()) == 0
