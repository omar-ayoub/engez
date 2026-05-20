import pytest


pytestmark = pytest.mark.asyncio


async def test_list_vendors(auth_client, seed_data):
    resp = await auth_client.get("/api/v1/vendors/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["vendors"]) >= 1
    vendor = data["vendors"][0]
    assert vendor["name"] == "Cement Egypt"
    assert vendor["name_ar"] == "أسمنت مصر"
    assert vendor["tax_registration"] == "123456789"


async def test_search_vendors_by_name(auth_client, seed_data):
    resp = await auth_client.get("/api/v1/vendors/search?q=Cement")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["vendors"]) >= 1
    assert data["vendors"][0]["name"] == "Cement Egypt"


async def test_search_vendors_by_name_ar(auth_client, seed_data):
    resp = await auth_client.get("/api/v1/vendors/search?q=%D8%A3%D8%B3%D9%85%D9%86%D8%AA")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["vendors"]) >= 1


async def test_search_vendors_by_tax_reg(auth_client, seed_data):
    resp = await auth_client.get("/api/v1/vendors/search?q=123456")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["vendors"]) >= 1


async def test_search_vendors_no_results(auth_client, seed_data):
    resp = await auth_client.get("/api/v1/vendors/search?q=zzznonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["vendors"]) == 0


async def test_search_vendors_min_length(auth_client, seed_data):
    resp = await auth_client.get("/api/v1/vendors/search?q=a")
    assert resp.status_code == 422
