import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from unittest.mock import MagicMock, patch

from tests.conftest import test_engine
from app.core.config import settings
from app.worker import (
    send_confirmation_email_task,
    send_invitation_email_task,
    notify_subscribers,
)

FRONTEND = "https://app.statusforge.test"
API = "https://api.statusforge.test"


@pytest.fixture(autouse=True)
def distinct_urls(monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_URL", FRONTEND)
    monkeypatch.setattr(settings, "APP_URL", API)
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")
    monkeypatch.setattr("app.worker.engine", test_engine)


def _ok_response():
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    return resp


@pytest.mark.asyncio
async def test_invitation_email_links_to_frontend_accept_page():
    with patch("httpx.AsyncClient.post") as post:
        post.return_value = _ok_response()
        await send_invitation_email_task({}, "invitee@example.com", "raw-token-abc")
    body = post.call_args[1]["json"]
    expected = f"{FRONTEND}/invitations/accept?token=raw-token-abc"
    assert expected in body["html"]
    assert expected in body["text"]
    assert API not in body["html"] and API not in body["text"]


@pytest.mark.asyncio
async def test_confirmation_email_links_to_frontend_confirm_page():
    with patch("httpx.AsyncClient.post") as post:
        post.return_value = _ok_response()
        await send_confirmation_email_task({}, "s@example.com", "conf-tok", "Org", "org")
    body = post.call_args[1]["json"]
    assert f"{FRONTEND}/subscribers/confirm/conf-tok" in body["html"]
    assert API not in body["html"]


@pytest.mark.asyncio
async def test_incident_notification_links_to_frontend_status_and_unsubscribe(client: AsyncClient):
    await client.post(
        "/auth/bootstrap",
        json={"organization_name": "Link Org"},
        headers={"Authorization": "Bearer mock-uid-linkuser"},
    )
    orgs = (await client.get("/organizations", headers={"Authorization": "Bearer mock-uid-linkuser"})).json()
    slug = orgs[0]["slug"]
    hdr = {"Authorization": "Bearer mock-uid-linkuser", "X-Organization-Slug": slug}

    svc = await client.post("/services", json={"name": "API"}, headers=hdr)
    await client.post(f"/status/{slug}/subscribe", json={"email": "sub@example.com"})
    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text(
            "SELECT confirmation_token, unsubscribe_token FROM subscriber WHERE email='sub@example.com'"
        ))).fetchone()
    conf_token, unsub_token = row
    assert (await client.get(f"/subscribers/confirm/{conf_token}")).status_code == 200

    inc = await client.post(
        "/incidents",
        json={"title": "Down", "impact": "MAJOR", "service_ids": [svc.json()["id"]], "message": "Investigating"},
        headers=hdr,
    )

    with patch("httpx.AsyncClient.post") as post:
        post.return_value = _ok_response()
        await notify_subscribers({}, inc.json()["id"])

    body = post.call_args[1]["json"]
    assert f"{FRONTEND}/status/{slug}" in body["html"]
    assert f"{FRONTEND}/subscribers/unsubscribe/{unsub_token}" in body["html"]
    assert API not in body["html"]
