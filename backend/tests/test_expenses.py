import pytest
import uuid


pytestmark = pytest.mark.asyncio


async def test_create_expense(auth_client, seed_data):
    payload = {
        "offline_id": str(uuid.uuid4()),
        "amount": 150.50,
        "currency": "EGP",
        "vendor": "Cement Egypt",
        "items": "50 bags cement",
        "category_id": seed_data["category"].id,
        "project_id": seed_data["project"].id,
        "capture_mode": "manual",
    }
    resp = await auth_client.post("/api/v1/expenses/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == 150.50
    assert data["vendor"] == "Cement Egypt"
    assert data["capture_mode"] == "manual"
    assert data["status"] == "pending"
    assert data["id"] is not None


async def test_create_expense_voice_mode(auth_client, seed_data):
    payload = {
        "offline_id": str(uuid.uuid4()),
        "amount": 200.0,
        "currency": "EGP",
        "vendor": "",
        "items": "",
        "capture_mode": "voice",
        "voice_url": "https://r2.example.com/voice/test.webm",
        "voice_transcript": "مصاريف أسمنت ميتين جنيه",
        "ai_extraction": {"amount": 200, "vendor": None, "category": "materials"},
        "ai_confidence": {"amount": 0.95, "vendor": 0.2, "category": 0.8},
    }
    resp = await auth_client.post("/api/v1/expenses/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["capture_mode"] == "voice"


async def test_create_expense_receipt_mode(auth_client, seed_data):
    payload = {
        "offline_id": str(uuid.uuid4()),
        "amount": 350.0,
        "currency": "EGP",
        "vendor": "Hardware Store",
        "items": "",
        "capture_mode": "receipt",
        "receipt_url": "https://r2.example.com/receipt/test.jpg",
        "eta_uuid": "abc123def456",
        "eta_verified": True,
        "ai_extraction": {"amount": 350, "vendor": "Hardware Store"},
        "ai_confidence": {"amount": 0.99},
    }
    resp = await auth_client.post("/api/v1/expenses/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["capture_mode"] == "receipt"
    assert data["eta_verified"] is True


async def test_create_expense_duplicate_offline_id(auth_client, seed_data):
    offline_id = str(uuid.uuid4())
    payload = {
        "offline_id": offline_id,
        "amount": 100.0,
        "vendor": "Test",
        "items": "",
        "capture_mode": "manual",
    }
    resp1 = await auth_client.post("/api/v1/expenses/", json=payload)
    assert resp1.status_code == 201

    resp2 = await auth_client.post("/api/v1/expenses/", json=payload)
    assert resp2.status_code == 409
    assert "already submitted" in resp2.json()["detail"]["detail_en"]


async def test_list_expenses(auth_client, seed_data):
    for i in range(3):
        await auth_client.post("/api/v1/expenses/", json={
            "offline_id": str(uuid.uuid4()),
            "amount": 50.0 + i,
            "vendor": f"Vendor {i}",
            "items": "",
            "capture_mode": "manual",
        })

    resp = await auth_client.get("/api/v1/expenses/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3
    assert "pages" in data


async def test_list_expenses_filter_by_status(auth_client, seed_data):
    resp = await auth_client.get("/api/v1/expenses/?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["status"] == "pending"


async def test_list_expenses_filter_by_capture_mode(auth_client, seed_data):
    await auth_client.post("/api/v1/expenses/", json={
        "offline_id": str(uuid.uuid4()),
        "amount": 75.0,
        "vendor": "Voice Vendor",
        "items": "",
        "capture_mode": "voice",
    })

    resp = await auth_client.get("/api/v1/expenses/?capture_mode=voice")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["capture_mode"] == "voice"


async def test_update_expense(auth_client, seed_data):
    create_resp = await auth_client.post("/api/v1/expenses/", json={
        "offline_id": str(uuid.uuid4()),
        "amount": 100.0,
        "vendor": "Original",
        "items": "",
        "capture_mode": "manual",
    })
    expense_id = create_resp.json()["id"]

    resp = await auth_client.patch(f"/api/v1/expenses/{expense_id}", json={
        "amount": 120.0,
        "vendor": "Updated",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["amount"] == 120.0
    assert data["vendor"] == "Updated"


async def test_update_expense_not_found(auth_client, seed_data):
    resp = await auth_client.patch("/api/v1/expenses/nonexistent", json={
        "amount": 50.0,
    })
    assert resp.status_code == 404


async def test_update_expense_with_ai_correction_feedback(auth_client, seed_data, db_session):
    create_resp = await auth_client.post("/api/v1/expenses/", json={
        "offline_id": str(uuid.uuid4()),
        "amount": 100.0,
        "vendor": "AI Vendor",
        "items": "cement",
        "capture_mode": "voice",
        "ai_extraction": {"amount": 100.0, "vendor": "AI Vendor", "items": "cement"},
    })
    expense_id = create_resp.json()["id"]

    resp = await auth_client.patch(f"/api/v1/expenses/{expense_id}", json={
        "vendor": "Corrected Vendor",
    })
    assert resp.status_code == 200

    from sqlalchemy import select
    from app.models.correction import CorrectionFeedback
    result = await db_session.execute(
        select(CorrectionFeedback).where(
            CorrectionFeedback.expense_id == expense_id,
            CorrectionFeedback.field_name == "vendor",
        )
    )
    feedback = result.scalar_one_or_none()
    assert feedback is not None
    assert feedback.ai_value == "AI Vendor"
    assert feedback.corrected_value == "Corrected Vendor"
