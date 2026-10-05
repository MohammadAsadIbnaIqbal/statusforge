import pytest
from httpx import AsyncClient
from app.models.membership import Role
from sqlmodel import select
from app.models.organization import Organization
from app.models.membership import Membership

async def bootstrap_user(client: AsyncClient, num: int):
    await client.post(
        "/auth/bootstrap",
        json={"organization_name": f"Org {num}"},
        headers={"Authorization": f"Bearer mock-uid-{num}"}
    )
    me_resp = await client.get("/organizations", headers={"Authorization": f"Bearer mock-uid-{num}"})
    return f"mock-uid-{num}", me_resp.json()[0]["slug"], me_resp.json()[0]["id"]

@pytest.mark.asyncio
async def test_transfer_ownership(client: AsyncClient, test_session, monkeypatch):
    enqueued = []
    async def mock_enqueue(self, job_name, *args, **kwargs):
        enqueued.append((job_name, kwargs))

    mock_redis = type("MockRedis", (), {"enqueue_job": mock_enqueue})()
    async def mock_cp(*args, **kwargs): return mock_redis
    monkeypatch.setattr("app.routers.invitations.create_pool", mock_cp)

    token1, slug1, org_id1 = await bootstrap_user(client, 1001)

    # invite user 2
    inv_res = await client.post(
        "/invitations",
        json={"email": "newowner@example.com", "role": "ADMIN"},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    assert inv_res.status_code == 201
    raw_token = enqueued[0][1]["token"]

    await bootstrap_user(client, "newowner")
    acc_res = await client.post(
        f"/invitations/{raw_token}/accept",
        headers={"Authorization": "Bearer mock-uid-newowner"}
    )
    assert acc_res.status_code == 200

    # get user id of newowner
    members_res = await client.get(
        f"/organizations/{org_id1}/members",
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    members = members_res.json()
    newowner_id = next(m["user_id"] for m in members if m["role"] == "ADMIN")
    oldowner_id = next(m["user_id"] for m in members if m["role"] == "OWNER")

    # self-transfer should fail
    self_trans_res = await client.post(
        f"/organizations/{org_id1}/transfer_ownership",
        json={"new_owner_user_id": oldowner_id},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    assert self_trans_res.status_code == 400

    # transfer ownership
    trans_res = await client.post(
        f"/organizations/{org_id1}/transfer_ownership",
        json={"new_owner_user_id": newowner_id},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    assert trans_res.status_code == 200, trans_res.json()

    # verify roles changed
    m1 = (await test_session.exec(select(Membership).where(Membership.organization_id == org_id1, Membership.role == Role.OWNER))).first()
    assert m1.user_id == newowner_id

    # Try to transfer again (should fail because user 1 is now ADMIN, not OWNER)
    trans_res2 = await client.post(
        f"/organizations/{org_id1}/transfer_ownership",
        json={"new_owner_user_id": newowner_id},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    assert trans_res2.status_code == 403

@pytest.mark.asyncio
async def test_delete_organization(client: AsyncClient, test_session, monkeypatch):
    enqueued = []
    async def mock_enqueue(self, job_name, *args, **kwargs):
        enqueued.append((job_name, kwargs))

    mock_redis = type("MockRedis", (), {"enqueue_job": mock_enqueue})()
    async def mock_cp(*args, **kwargs): return mock_redis
    monkeypatch.setattr("app.routers.invitations.create_pool", mock_cp)

    token1, slug1, org_id1 = await bootstrap_user(client, 1002)
    token2, slug2, org_id2 = await bootstrap_user(client, 1003)

    # User 1 invites user 2 as ADMIN
    inv_res = await client.post(
        "/invitations",
        json={"email": "1003@example.com", "role": "ADMIN"},
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    raw_token = enqueued[0][1]["token"]

    # User 2 accepts (so user 2 is ADMIN in org 1)
    client.headers = {}
    await client.post(
        f"/invitations/{raw_token}/accept",
        headers={"Authorization": f"Bearer {token2}"}
    )

    # Non-owner (User 2 as ADMIN) cannot delete org 1
    del_res_unauth = await client.delete(
        f"/organizations/{org_id1}",
        headers={"Authorization": f"Bearer {token2}", "X-Organization-Slug": slug1}
    )
    assert del_res_unauth.status_code == 403

    # Cross-org deletion attempt: User 2 tries to delete org 1 while passing slug2 (fails because slug mismatch or forbidden)
    del_res_cross = await client.delete(
        f"/organizations/{org_id1}",
        headers={"Authorization": f"Bearer {token2}", "X-Organization-Slug": slug2}
    )
    assert del_res_cross.status_code == 403

    # Owner deletes org 1
    del_res = await client.delete(
        f"/organizations/{org_id1}",
        headers={"Authorization": f"Bearer {token1}", "X-Organization-Slug": slug1}
    )
    assert del_res.status_code == 204

    # Assert org is gone
    org = (await test_session.exec(select(Organization).where(Organization.id == org_id1))).first()
    assert org is None

    # Assert memberships are gone
    mems = (await test_session.exec(select(Membership).where(Membership.organization_id == org_id1))).all()
    assert len(mems) == 0

    # Assert org 2 is still intact
    org2 = (await test_session.exec(select(Organization).where(Organization.id == org_id2))).first()
    assert org2 is not None





# ---------------------------------------------------------------------------
# Ownership-transfer invariants and full-cascade deletion regression tests
# ---------------------------------------------------------------------------
from app.models.user import User
from app.models.invitation import Invitation
from app.models.service import Service
from app.models.subscriber import Subscriber
from app.models.incident import Incident, IncidentUpdate, IncidentServiceLink


def _hdr(token: str, slug: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}


async def _join_org(client: AsyncClient, monkeypatch, owner_token: str, owner_slug: str, uid: str, role: str):
    """Invite `<uid>@example.com` into the owner's org via the API and accept as that user."""
    captured = []

    async def mock_enqueue(self, job_name, *args, **kwargs):
        captured.append(kwargs)

    mock_redis = type("MockRedis", (), {"enqueue_job": mock_enqueue})()

    async def mock_cp(*args, **kwargs):
        return mock_redis

    monkeypatch.setattr("app.routers.invitations.create_pool", mock_cp)

    res = await client.post(
        "/invitations",
        json={"email": f"{uid}@example.com", "role": role},
        headers=_hdr(owner_token, owner_slug),
    )
    assert res.status_code == 201, res.json()
    raw_token = captured[-1]["token"]

    await bootstrap_user(client, uid)
    acc = await client.post(
        f"/invitations/{raw_token}/accept",
        headers={"Authorization": f"Bearer mock-uid-{uid}"},
    )
    assert acc.status_code == 200, acc.json()


async def _members(client: AsyncClient, token: str, slug: str, org_id: int):
    res = await client.get(f"/organizations/{org_id}/members", headers=_hdr(token, slug))
    assert res.status_code == 200
    return res.json()


@pytest.mark.asyncio
async def test_transfer_ownership_enforces_owner_invariant(client: AsyncClient, test_session, monkeypatch):
    owner_tok, slug, org_id = await bootstrap_user(client, "xferowner")
    await _join_org(client, monkeypatch, owner_tok, slug, "xferadmin", "ADMIN")
    await _join_org(client, monkeypatch, owner_tok, slug, "xfermember", "MEMBER")
    await bootstrap_user(client, "xferoutsider")  # has own org only; NOT a member of `org_id`

    members = await _members(client, owner_tok, slug, org_id)
    by_role = {m["role"]: m["user_id"] for m in members}
    owner_id, admin_id = by_role["OWNER"], by_role["ADMIN"]
    member_id = by_role["MEMBER"]
    outsider_id = (await test_session.exec(select(User).where(User.firebase_uid == "xferoutsider"))).one().id

    url = f"/organizations/{org_id}/transfer_ownership"

    # Non-owners (ADMIN and MEMBER) cannot transfer.
    for uid in ("xferadmin", "xfermember"):
        res = await client.post(url, json={"new_owner_user_id": member_id}, headers=_hdr(f"mock-uid-{uid}", slug))
        assert res.status_code == 403, uid

    # Self-transfer is rejected and does not change roles.
    res = await client.post(url, json={"new_owner_user_id": owner_id}, headers=_hdr(owner_tok, slug))
    assert res.status_code == 400

    # Target outside the organization is rejected.
    res = await client.post(url, json={"new_owner_user_id": outsider_id}, headers=_hdr(owner_tok, slug))
    assert res.status_code == 404

    # Nonexistent target is rejected.
    res = await client.post(url, json={"new_owner_user_id": 999999}, headers=_hdr(owner_tok, slug))
    assert res.status_code == 404

    # None of the rejected attempts changed anything: still exactly one OWNER (the original).
    test_session.expire_all()
    owners = (await test_session.exec(
        select(Membership).where(Membership.organization_id == org_id, Membership.role == Role.OWNER)
    )).all()
    assert [m.user_id for m in owners] == [owner_id]

    # Valid transfer succeeds.
    res = await client.post(url, json={"new_owner_user_id": admin_id}, headers=_hdr(owner_tok, slug))
    assert res.status_code == 200

    test_session.expire_all()
    memberships = (await test_session.exec(
        select(Membership).where(Membership.organization_id == org_id)
    )).all()
    role_of = {m.user_id: m.role for m in memberships}
    assert sum(1 for r in role_of.values() if r == Role.OWNER) == 1
    assert role_of[admin_id] == Role.OWNER
    assert role_of[owner_id] == Role.ADMIN
    assert role_of[member_id] == Role.MEMBER

    # The former owner (now ADMIN) can no longer perform owner-only transfers.
    res = await client.post(url, json={"new_owner_user_id": owner_id}, headers=_hdr(owner_tok, slug))
    assert res.status_code == 403
    res = await client.post(url, json={"new_owner_user_id": member_id}, headers=_hdr(owner_tok, slug))
    assert res.status_code == 403

    # And the new owner can.
    res = await client.post(url, json={"new_owner_user_id": owner_id}, headers=_hdr("mock-uid-xferadmin", slug))
    assert res.status_code == 200


async def _populate_org(client: AsyncClient, monkeypatch, token: str, slug: str, sub_email: str):
    """Create a service, incident (+ link), incident update, subscriber and pending invitation."""
    svc = await client.post("/services", json={"name": "API"}, headers=_hdr(token, slug))
    assert svc.status_code == 201
    inc = await client.post(
        "/incidents",
        json={
            "title": "Outage", "impact": "MAJOR", "status": "INVESTIGATING",
            "message": "Looking into it", "service_ids": [svc.json()["id"]],
        },
        headers=_hdr(token, slug),
    )
    assert inc.status_code == 201
    upd = await client.post(
        f"/incidents/{inc.json()['id']}/updates",
        json={"status": "MONITORING", "message": "Fix deployed"},
        headers=_hdr(token, slug),
    )
    assert upd.status_code == 200
    sub = await client.post(f"/status/{slug}/subscribe", json={"email": sub_email})
    assert sub.status_code == 201

    async def mock_enqueue(self, job_name, *args, **kwargs):
        return None

    mock_redis = type("MockRedis", (), {"enqueue_job": mock_enqueue})()

    async def mock_cp(*args, **kwargs):
        return mock_redis

    monkeypatch.setattr("app.routers.invitations.create_pool", mock_cp)
    inv = await client.post(
        "/invitations",
        json={"email": f"pending-{sub_email}", "role": "MEMBER"},
        headers=_hdr(token, slug),
    )
    assert inv.status_code == 201


async def _org_counts(session, org_id: int) -> dict:
    session.expire_all()
    incident_ids = [i.id for i in (await session.exec(select(Incident).where(Incident.organization_id == org_id))).all()]
    return {
        "memberships": len((await session.exec(select(Membership).where(Membership.organization_id == org_id))).all()),
        "invitations": len((await session.exec(select(Invitation).where(Invitation.organization_id == org_id))).all()),
        "services": len((await session.exec(select(Service).where(Service.organization_id == org_id))).all()),
        "incidents": len(incident_ids),
        "updates": len((await session.exec(select(IncidentUpdate).where(IncidentUpdate.incident_id.in_(incident_ids)))).all()) if incident_ids else 0,
        "links": len((await session.exec(select(IncidentServiceLink).where(IncidentServiceLink.incident_id.in_(incident_ids)))).all()) if incident_ids else 0,
        "subscribers": len((await session.exec(select(Subscriber).where(Subscriber.organization_id == org_id))).all()),
    }


@pytest.mark.asyncio
async def test_delete_organization_cascades_only_its_own_data(client: AsyncClient, test_session, monkeypatch):
    tok_a, slug_a, org_a = await bootstrap_user(client, "delownera")
    tok_b, slug_b, org_b = await bootstrap_user(client, "delownerb")

    await _populate_org(client, monkeypatch, tok_a, slug_a, "sub-a@example.com")
    await _populate_org(client, monkeypatch, tok_b, slug_b, "sub-b@example.com")

    before_a = await _org_counts(test_session, org_a)
    before_b = await _org_counts(test_session, org_b)
    assert all(v >= 1 for v in before_a.values()), before_a
    assert before_a == before_b

    # A non-owner member of org A cannot delete it.
    await _join_org(client, monkeypatch, tok_a, slug_a, "delmemberofa", "ADMIN")
    res = await client.delete(f"/organizations/{org_a}", headers=_hdr("mock-uid-delmemberofa", slug_a))
    assert res.status_code == 403
    assert (await _org_counts(test_session, org_a))["services"] == before_a["services"]

    # Owner of org B cannot delete org A (neither by id nor by mismatched header).
    for slug in (slug_a, slug_b):
        res = await client.delete(f"/organizations/{org_a}", headers=_hdr(tok_b, slug))
        assert res.status_code in (403, 404)
    assert (await _org_counts(test_session, org_a))["services"] == before_a["services"]

    # Owner deletes org A.
    res = await client.delete(f"/organizations/{org_a}", headers=_hdr(tok_a, slug_a))
    assert res.status_code == 204

    test_session.expire_all()
    assert (await test_session.exec(select(Organization).where(Organization.id == org_a))).first() is None
    after_a = await _org_counts(test_session, org_a)
    assert all(v == 0 for v in after_a.values()), after_a

    # Org B is untouched.
    assert (await test_session.exec(select(Organization).where(Organization.id == org_b))).first() is not None
    assert await _org_counts(test_session, org_b) == before_b

    # Users are never deleted along with an organization.
    for uid in ("delownera", "delownerb", "delmemberofa"):
        assert (await test_session.exec(select(User).where(User.firebase_uid == uid))).first() is not None
