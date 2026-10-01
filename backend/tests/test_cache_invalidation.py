from unittest.mock import ANY
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from tests.conftest import test_engine

async def register_user(client: AsyncClient, num: int):
    response = await client.post(
        "/register",
        json={"username": f"user{num}_cache", "password": "password", "email": f"user{num}_cache@example.com", "organization_name": f"Org {num} Cache"}
    )
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_incident_resolution_cache_invalidation(client: AsyncClient):
    # Mock create_pool to return our AsyncMock Redis
    mock_redis = AsyncMock()
    
    with patch("app.services.incident_service.create_pool", return_value=mock_redis):
        with patch("app.services.status_page_service.create_pool", return_value=mock_redis):
            
            token = await register_user(client, 1)
            
            # Create a service
            res_s = await client.post("/services", headers={"Authorization": f"Bearer {token}"}, json={"name": "API"})
            s_id = res_s.json()["id"]
            
            # Create incident
            res_inc = await client.post(
                "/incidents", 
                headers={"Authorization": f"Bearer {token}"},
                json={"title": "API Down", "status": "INVESTIGATING", "impact": "CRITICAL", "service_ids": [s_id], "message": "Investigating"}
            )
            inc_id = res_inc.json()["id"]
            
            # Verify cache invalidation was enqueued for the correct key on creation
            mock_redis.enqueue_job.assert_any_call("invalidate_cache", "statusforge:status:org-1-cache")
            
            # Read public status (should write to cache)
            mock_redis.get.return_value = None # Simulate cache miss
            res_pub = await client.get("/status/org-1-cache")
            assert res_pub.status_code == 200
            
            # Verify setex was called with the correct key
            mock_redis.setex.assert_called_with("statusforge:status:org-1-cache", 30, ANY)
            
            # Resolve incident
            res_upd = await client.post(
                f"/incidents/{inc_id}/updates", 
                headers={"Authorization": f"Bearer {token}"},
                json={"status": "RESOLVED", "message": "Fixed"}
            )
            assert res_upd.status_code == 200
            
            # Verify cache invalidation enqueued AGAIN with the exact correct key upon resolution
            mock_redis.enqueue_job.assert_called_with("notify_subscribers", incident_id=inc_id)
            mock_redis.enqueue_job.assert_any_call("invalidate_cache", "statusforge:status:org-1-cache")
