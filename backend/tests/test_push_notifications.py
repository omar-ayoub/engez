import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vapid_public_key(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/notifications/vapid-public-key")
    assert resp.status_code in (200, 503)


@pytest.mark.asyncio
async def test_subscribe(admin_client: AsyncClient):
    resp = await admin_client.put(
        "/api/v1/notifications/subscription",
        json={
            "endpoint": "https://push.example.com/send/abc",
            "expirationTime": None,
            "keys": {"p256dh": "test-key", "auth": "test-auth"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subscribed"] is True


@pytest.mark.asyncio
async def test_unsubscribe(admin_client: AsyncClient):
    await admin_client.put(
        "/api/v1/notifications/subscription",
        json={
            "endpoint": "https://push.example.com/send/abc",
            "expirationTime": None,
            "keys": {"p256dh": "test-key", "auth": "test-auth"},
        },
    )

    resp = await admin_client.delete("/api/v1/notifications/subscription")
    assert resp.status_code == 200
    data = resp.json()
    assert data["subscribed"] is False


@pytest.mark.asyncio
async def test_subscribe_invalid_endpoint(admin_client: AsyncClient):
    resp = await admin_client.put(
        "/api/v1/notifications/subscription",
        json={
            "endpoint": "http://not-https.example.com",
            "expirationTime": None,
            "keys": {"p256dh": "test", "auth": "test"},
        },
    )
    assert resp.status_code == 422
