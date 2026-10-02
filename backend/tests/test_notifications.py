import pytest
import httpx
from unittest.mock import patch, MagicMock
from app.core.config import settings
from app.services.email_service import get_email_service, ResendEmailService
from app.worker import send_welcome_email_task, send_confirmation_email_task, notify_subscribers
from app.models.incident import IncidentCreate
from tests.conftest import test_engine
import sqlalchemy as sa

@pytest.fixture
def mock_httpx_post():
    with patch("httpx.AsyncClient.post") as mock_post:
        yield mock_post

@pytest.mark.asyncio
async def test_email_service_log_mode(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "log")
    service = get_email_service()

    await service.send_email("test@example.com", "Subj", "<p>HTML</p>", "TEXT")

    # Assert no HTTP calls made
    mock_httpx_post.assert_not_called()

@pytest.mark.asyncio
async def test_email_service_live_mode_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", None)

    with pytest.raises(ValueError, match="EMAIL_PROVIDER_API_KEY is not set"):
        get_email_service()

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
    args, kwargs = mock_httpx_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test_key"
    assert kwargs["json"]["to"] == ["test@example.com"]
    assert kwargs["json"]["subject"] == "Subj"
    assert kwargs["json"]["from"] == settings.EMAIL_SENDER

@pytest.mark.asyncio
async def test_email_service_live_mode_timeout(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")

    mock_httpx_post.side_effect = httpx.RequestError("Timeout")

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
    # 403 should be caught and return silently to prevent retry loops
    await service.send_email("test@example.com", "Subj", "<p>HTML</p>", "TEXT")

@pytest.mark.asyncio
async def test_email_service_live_mode_http_error_temporary(mock_httpx_post, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "live")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER_API_KEY", "test_key")

    mock_req = MagicMock()
    mock_resp = httpx.Response(502, request=mock_req, text="Bad Gateway")
    mock_httpx_post.side_effect = httpx.HTTPStatusError("Err", request=mock_req, response=mock_resp)

    service = get_email_service()
    # 502 should be re-raised so ARQ retries
    with pytest.raises(httpx.HTTPStatusError):
        await service.send_email("test@example.com", "Subj", "<p>HTML</p>", "TEXT")

# Now let's test the worker functions natively
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

    # 1. Setup DB state
    res = await client.post(
        "/register",
        json={"username": "notifuser", "password": "password", "email": "n@example.com", "organization_name": "OrgN"}
    )
    token = res.json()["access_token"]

    # Create service
    s_res = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "API"})
    s_id = s_res.json()["id"]

    # Subscribe and confirm
    await client.post("/status/orgn/subscribe", json={"email": "sub1@test.com"})

    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token FROM subscriber WHERE email='sub1@test.com'"))).fetchone()
        conf_token = row[0]
    await client.get(f"/subscribers/confirm/{conf_token}")

    # Create incident
    inc_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "DB Down", "impact": "CRITICAL", "service_ids": [s_id], "message": "Investigating..."}
    )
    inc_id = inc_res.json()["id"]

    # Run worker function directly
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

    # 1. Setup DB state
    res = await client.post(
        "/register",
        json={"username": "notifel", "password": "password", "email": "n2@example.com", "organization_name": "OrgEl"}
    )
    token = res.json()["access_token"]

    # Create service
    s_res = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "API2"})
    s_id = s_res.json()["id"]

    # Subscribe 1 (confirmed)
    await client.post("/status/orgel/subscribe", json={"email": "conf@test.com"})
    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token, unsubscribe_token FROM subscriber WHERE email='conf@test.com'"))).fetchone()
        conf_token = row[0]
        unsub_token = row[1]
    await client.get(f"/subscribers/confirm/{conf_token}")

    # Subscribe 2 (unconfirmed)
    await client.post("/status/orgel/subscribe", json={"email": "unconf@test.com"})

    # Subscribe 3 (confirmed then unsubscribed)
    await client.post("/status/orgel/subscribe", json={"email": "unsubbed@test.com"})
    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token, unsubscribe_token FROM subscriber WHERE email='unsubbed@test.com'"))).fetchone()
        conf_token3 = row[0]
        unsub_token3 = row[1]
    await client.get(f"/subscribers/confirm/{conf_token3}")
    await client.get(f"/subscribers/unsubscribe/{unsub_token3}")

    # Create incident
    inc_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "DB Down 2", "impact": "CRITICAL", "service_ids": [s_id], "message": "Investigating..."}
    )
    inc_id = inc_res.json()["id"]

    # Run worker function directly
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post") as mock_httpx_post:
        mock_httpx_post.return_value = mock_resp
        await notify_subscribers({}, inc_id)

        # Should only be called ONCE (for conf@test.com)
        mock_httpx_post.assert_called_once()
        kwargs = mock_httpx_post.call_args[1]
        assert kwargs["json"]["to"] == ["conf@test.com"]

@pytest.mark.asyncio
async def test_worker_notify_subscribers_log_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MODE", "log")
    monkeypatch.setattr("app.worker.engine", test_engine)

    # Setup DB state
    res = await client.post(
        "/register",
        json={"username": "notiflog", "password": "password", "email": "nlog@example.com", "organization_name": "OrgLog"}
    )
    token = res.json()["access_token"]

    s_res = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "API_Log"})
    s_id = s_res.json()["id"]

    await client.post("/status/orglog/subscribe", json={"email": "logsub@test.com"})
    async with test_engine.connect() as conn:
        row = (await conn.execute(sa.text("SELECT confirmation_token FROM subscriber WHERE email='logsub@test.com'"))).fetchone()
        conf_token = row[0]
    await client.get(f"/subscribers/confirm/{conf_token}")

    inc_res = await client.post(
        "/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Log Incident", "impact": "MINOR", "service_ids": [s_id], "message": "Testing..."}
    )
    inc_id = inc_res.json()["id"]

    # The worker task should run and return {"status": "sent"}
    result = await notify_subscribers({}, inc_id)
    assert result["status"] == "sent"
