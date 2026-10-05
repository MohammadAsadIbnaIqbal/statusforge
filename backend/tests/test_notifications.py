import pytest
from httpx import AsyncClient
import sqlalchemy as sa
import httpx
from unittest.mock import MagicMock, patch
from tests.conftest import test_engine
from app.core.config import settings
from app.services.email_service import get_email_service
from app.worker import send_confirmation_email_task, notify_subscribers

async def bootstrap_user(client: AsyncClient, num: int):
    await client.post(
        "/auth/bootstrap",
        json={"organization_name": f"Org {num}"},
        headers={"Authorization": f"Bearer mock-uid-{num}"}
    )
    me_resp = await client.get("/organizations", headers={"Authorization": f"Bearer mock-uid-{num}"})
    return f"mock-uid-{num}", me_resp.json()[0]["slug"], me_resp.json()[0]["id"]

@pytest.fixture
def mock_httpx_post():
    with patch("httpx.AsyncClient.post") as m:
        yield m

@pytest.mark.asyncio
async def test_email_service_log_mode(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "log")
    service = get_email_service()
    await service.send_email("test@example.com", "Subj", "<p>HTML</p>", "TEXT")
    mock_httpx_post.assert_not_called()

@pytest.mark.asyncio
async def test_email_service_live_mode_success(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_httpx_post.return_value = mock_resp

    service = get_email_service()
    await service.send_email("test@example.com", "Subj", "<p>HTML</p>", "TEXT")

    mock_httpx_post.assert_called_once()
    kwargs = mock_httpx_post.call_args[1]
    assert kwargs["headers"]["Authorization"] == "Bearer test_key"
    assert kwargs["json"]["to"] == ["test@example.com"]
    assert kwargs["json"]["subject"] == "Subj"

@pytest.mark.asyncio
async def test_email_service_live_mode_no_key(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", None)

    with pytest.raises(ValueError):
        service = get_email_service()("test@example.com", "Subj", "<p>HTML</p>", "TEXT")

@pytest.mark.asyncio
async def test_email_service_live_mode_network_error(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")
    mock_httpx_post.side_effect = httpx.RequestError("Network error")

    service = get_email_service()
    with pytest.raises(httpx.RequestError):
        await service.send_email("test@example.com", "Subj", "<p>HTML</p>", "TEXT")

@pytest.mark.asyncio
async def test_email_service_live_mode_http_error_permanent(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")
    mock_req = MagicMock()
    mock_resp = httpx.Response(403, request=mock_req, text="Forbidden")
    mock_httpx_post.side_effect = httpx.HTTPStatusError("Err", request=mock_req, response=mock_resp)

    service = get_email_service()
    await service.send_email("test@example.com", "Subj", "<p>HTML</p>", "TEXT")

@pytest.mark.asyncio
async def test_email_service_live_mode_http_error_temporary(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")
    mock_req = MagicMock()
    mock_resp = httpx.Response(502, request=mock_req, text="Bad Gateway")
    mock_httpx_post.side_effect = httpx.HTTPStatusError("Err", request=mock_req, response=mock_resp)

    service = get_email_service()
    with pytest.raises(httpx.HTTPStatusError):
        await service.send_email("test@example.com", "Subj", "<p>HTML</p>", "TEXT")

@pytest.mark.asyncio
async def test_worker_send_confirmation(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_httpx_post.return_value = mock_resp

    await send_confirmation_email_task({}, "test@example.com", "tok123", "Org", "org")

    mock_httpx_post.assert_called_once()
    kwargs = mock_httpx_post.call_args[1]
    assert "tok123" in kwargs["json"]["html"]
    assert "Org" in kwargs["json"]["html"]

@pytest.mark.asyncio
async def test_worker_notify_subscribers(client, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")
    monkeypatch.setattr("app.worker.engine", test_engine)

    token, slug, _ = await bootstrap_user(client, 1)

    s_res = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "API"})
    s_id = s_res.json()["id"]

    await client.post(f"/status/{slug}/subscribe", json={"email": "sub1@test.com"})

    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token FROM subscriber WHERE email='sub1@test.com'"))).fetchone()
        conf_token = row[0]
    await client.get(f"/subscribers/confirm/{conf_token}")

    inc_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"title": "DB Down", "impact": "CRITICAL", "service_ids": [s_id], "message": "Investigating..."}
    )
    inc_id = inc_res.json()["id"]

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post") as mock_httpx_post:
        mock_httpx_post.return_value = mock_resp
        await notify_subscribers({}, inc_id)

        mock_httpx_post.assert_called_once()
        kwargs = mock_httpx_post.call_args[1]
        assert kwargs["json"]["to"] == ["sub1@test.com"]
        assert "DB Down" in kwargs["json"]["subject"]
        assert "CRITICAL" in kwargs["json"]["html"]
        assert "Investigating..." in kwargs["json"]["html"]
        assert "API" in kwargs["json"]["html"]
        assert "unsubscribe" in kwargs["json"]["html"].lower()

@pytest.mark.asyncio
async def test_worker_notify_subscribers_eligibility(client, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")
    monkeypatch.setattr("app.worker.engine", test_engine)

    token, slug, _ = await bootstrap_user(client, 2)

    s_res = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "API2"})
    s_id = s_res.json()["id"]

    await client.post(f"/status/{slug}/subscribe", json={"email": "conf@test.com"})
    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token, unsubscribe_token FROM subscriber WHERE email='conf@test.com'"))).fetchone()
        conf_token = row[0]
        unsub_token = row[1]
    await client.get(f"/subscribers/confirm/{conf_token}")

    await client.post(f"/status/{slug}/subscribe", json={"email": "unconf@test.com"})

    await client.post(f"/status/{slug}/subscribe", json={"email": "unsubbed@test.com"})
    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token, unsubscribe_token FROM subscriber WHERE email='unsubbed@test.com'"))).fetchone()
        conf_token3 = row[0]
        unsub_token3 = row[1]
    await client.get(f"/subscribers/confirm/{conf_token3}")
    await client.get(f"/subscribers/unsubscribe/{unsub_token3}")

    inc_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"title": "DB Down 2", "impact": "CRITICAL", "service_ids": [s_id], "message": "Investigating..."}
    )
    inc_id = inc_res.json()["id"]

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post") as mock_httpx_post:
        mock_httpx_post.return_value = mock_resp
        await notify_subscribers({}, inc_id)
        mock_httpx_post.assert_called_once()
        kwargs = mock_httpx_post.call_args[1]
        assert kwargs["json"]["to"] == ["conf@test.com"]

@pytest.mark.asyncio
async def test_worker_notify_subscribers_log_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "log")
    monkeypatch.setattr("app.worker.engine", test_engine)

    token, slug, _ = await bootstrap_user(client, 3)

    s_res = await client.post("/services", headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug}, json={"name": "API_Log"})
    s_id = s_res.json()["id"]

    await client.post(f"/status/{slug}/subscribe", json={"email": "logsub@test.com"})
    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token FROM subscriber WHERE email='logsub@test.com'"))).fetchone()
        conf_token = row[0]
    await client.get(f"/subscribers/confirm/{conf_token}")

    inc_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}", "X-Organization-Slug": slug},
        json={"title": "Log Incident", "impact": "MINOR", "service_ids": [s_id], "message": "Testing..."}
    )
    inc_id = inc_res.json()["id"]

    result = await notify_subscribers({}, inc_id)
    assert result["status"] == "sent"
