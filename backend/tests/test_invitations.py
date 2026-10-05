import pytest
from httpx import AsyncClient
from app.models.membership import Role, Membership
from sqlmodel import select
from app.models.invitation import Invitation

async def bootstrap_user(client: AsyncClient, num: int):
    await client.post(
        "/auth/bootstrap",
        json={"organization_name": f"Org {num}"},
        headers={"Authorization": f"Bearer mock-uid-{num}"}
    )
    me_resp = await client.get("/organizations", headers={"Authorization": f"Bearer mock-uid-{num}"})
    return f"mock-uid-{num}", me_resp.json()[0]["slug"], me_resp.json()[0]["id"]

@pytest.mark.asyncio
async def test_create_and_accept_invitation(client: AsyncClient, test_session, monkeypatch):
    enqueued = []
    async def mock_enqueue(self, job_name, *args, **kwargs):
        enqueued.append((job_name, kwargs))

    mock_redis = type("MockRedis", (), {"enqueue_job": mock_enqueue})()
    async def mock_cp(*args, **kwargs): return mock_redis
    monkeypatch.setattr("app.routers.invitations.create_pool", mock_cp)

    token1, slug1, org_id1 = await bootstrap_user(client, 101)

    inv_res = await client.post(
        "/invitations",
        json={"email": "newuser@example.com", "role": "MEMBER"},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    assert inv_res.status_code == 201

    assert len(enqueued) == 1
    job_name, kwargs = enqueued[0]
    assert job_name == "send_invitation_email_task"
    raw_token = kwargs["token"]

    inv_id = inv_res.json()["id"]
    inv = (await test_session.exec(select(Invitation).where(Invitation.id == inv_id))).first()
    assert inv.token_hash != raw_token

    inv_res2 = await client.post(
        "/invitations",
        json={"email": "newuser@example.com", "role": "MEMBER"},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    assert inv_res2.status_code == 409

    await bootstrap_user(client, 102)
    acc_res_wrong = await client.post(
        f"/invitations/{raw_token}/accept",
        headers={"Authorization": "Bearer mock-uid-102"}
    )
    assert acc_res_wrong.status_code == 403

    await bootstrap_user(client, "newuser")
    acc_res = await client.post(
        f"/invitations/{raw_token}/accept",
        headers={"Authorization": "Bearer mock-uid-newuser"}
    )
    assert acc_res.status_code == 200

    acc_res2 = await client.post(
        f"/invitations/{raw_token}/accept",
        headers={"Authorization": "Bearer mock-uid-newuser"}
    )
    assert acc_res2.status_code == 400

@pytest.mark.asyncio
async def test_invitation_resend(client: AsyncClient, test_session, monkeypatch):
    enqueued = []
    async def mock_enqueue(self, job_name, *args, **kwargs):
        enqueued.append((job_name, kwargs))

    mock_redis = type("MockRedis", (), {"enqueue_job": mock_enqueue})()
    async def mock_cp(*args, **kwargs): return mock_redis
    monkeypatch.setattr("app.routers.invitations.create_pool", mock_cp)

    token1, slug1, org_id1 = await bootstrap_user(client, 201)

    inv_res = await client.post(
        "/invitations",
        json={"email": "resenduser@example.com", "role": "MEMBER"},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    inv_id = inv_res.json()["id"]
    old_raw_token = enqueued[0][1]["token"]
    enqueued.clear()

    resend_res = await client.post(
        f"/invitations/{inv_id}/resend",
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    assert resend_res.status_code == 200
    new_raw_token = enqueued[0][1]["token"]

    assert old_raw_token != new_raw_token

    await bootstrap_user(client, "resenduser")

    acc_old = await client.post(
        f"/invitations/{old_raw_token}/accept",
        headers={"Authorization": "Bearer mock-uid-resenduser"}
    )
    assert acc_old.status_code == 404

    acc_new = await client.post(
        f"/invitations/{new_raw_token}/accept",
        headers={"Authorization": "Bearer mock-uid-resenduser"}
    )
    assert acc_new.status_code == 200

@pytest.mark.asyncio
async def test_invitation_rbac(client: AsyncClient, test_session, monkeypatch):
    enqueued = []
    async def mock_enqueue(self, job_name, *args, **kwargs):
        enqueued.append((job_name, kwargs))

    mock_redis = type("MockRedis", (), {"enqueue_job": mock_enqueue})()
    async def mock_cp(*args, **kwargs): return mock_redis
    monkeypatch.setattr("app.routers.invitations.create_pool", mock_cp)

    token_owner, slug, _ = await bootstrap_user(client, 301)

    # OWNER invites ADMIN
    res = await client.post(
        "/invitations",
        json={"email": "admin301@example.com", "role": "ADMIN"},
        headers={"Authorization": f"Bearer {token_owner}", "X-Organization-Slug": slug}
    )
    assert res.status_code == 201
    admin_token = enqueued[0][1]["token"]
    enqueued.clear()

    # OWNER tries to invite OWNER
    res = await client.post(
        "/invitations",
        json={"email": "owner2@example.com", "role": "OWNER"},
        headers={"Authorization": f"Bearer {token_owner}", "X-Organization-Slug": slug}
    )
    assert res.status_code == 403

    # ADMIN accepts
    await bootstrap_user(client, "admin301")
    await client.post(
        f"/invitations/{admin_token}/accept",
        headers={"Authorization": "Bearer mock-uid-admin301"}
    )

    # ADMIN tries to invite ADMIN (should fail based on our business rule)
    res = await client.post(
        "/invitations",
        json={"email": "admin2@example.com", "role": "ADMIN"},
        headers={"Authorization": "Bearer mock-uid-admin301", "X-Organization-Slug": slug}
    )
    assert res.status_code == 403

    # ADMIN tries to invite MEMBER (should succeed)
    res = await client.post(
        "/invitations",
        json={"email": "member301@example.com", "role": "MEMBER"},
        headers={"Authorization": "Bearer mock-uid-admin301", "X-Organization-Slug": slug}
    )
    assert res.status_code == 201
    member_token = enqueued[0][1]["token"]
    enqueued.clear()

    # MEMBER accepts
    await bootstrap_user(client, "member301")
    await client.post(
        f"/invitations/{member_token}/accept",
        headers={"Authorization": "Bearer mock-uid-member301"}
    )

    # MEMBER tries to invite (should fail)
    res = await client.post(
        "/invitations",
        json={"email": "anyone@example.com", "role": "VIEWER"},
        headers={"Authorization": "Bearer mock-uid-member301", "X-Organization-Slug": slug}
    )
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_revoke_invitation(client: AsyncClient, monkeypatch):
    enqueued = []
    async def mock_enqueue(self, job_name, *args, **kwargs):
        enqueued.append((job_name, kwargs))

    mock_redis = type("MockRedis", (), {"enqueue_job": mock_enqueue})()
    async def mock_cp(*args, **kwargs): return mock_redis
    monkeypatch.setattr("app.routers.invitations.create_pool", mock_cp)

    token1, slug1, org_id1 = await bootstrap_user(client, 401)

    inv_res = await client.post(
        "/invitations",
        json={"email": "revoke@example.com", "role": "MEMBER"},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    inv_id = inv_res.json()["id"]
    raw_token = enqueued[0][1]["token"]

    rev_res = await client.delete(
        f"/invitations/{inv_id}",
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    assert rev_res.status_code == 204

    await bootstrap_user(client, "revoke")
    acc_res = await client.post(
        f"/invitations/{raw_token}/accept",
        headers={"Authorization": "Bearer mock-uid-revoke"}
    )
    assert acc_res.status_code == 400
    assert "no longer active" in acc_res.json()["detail"]
