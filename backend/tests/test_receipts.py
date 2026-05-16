import pytest
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio


async def test_receipt_extract_success(auth_client, seed_data):
    mock_extraction = {
        "amount": 450.0,
        "currency": "EGP",
        "vendor": "Cement Egypt",
        "date": "2026-05-15",
        "category": "materials",
        "line_items": [{"description": "cement", "amount": 450.0}],
        "confidence": {"amount": 0.9, "vendor": 0.85},
    }

    with patch("app.api.v1.receipts.upload_blob", new_callable=AsyncMock) as mock_upload, \
         patch("app.api.v1.receipts.process_receipt", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = (mock_extraction, False, None)
        mock_upload.return_value = "https://r2.example.com/receipts/test.jpg"

        image_content = b"\xff\xd8\xff\xe0fake jpeg data"
        resp = await auth_client.post(
            "/api/v1/receipts/extract",
            files={"image": ("receipt.jpg", image_content, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["extraction"]["amount"] == 450.0
        assert data["qr_detected"] is False
        assert data["receipt_url"] is not None


async def test_receipt_extract_with_qr(auth_client, seed_data):
    mock_extraction = {
        "amount": 1200.0,
        "vendor": "Tax Registered Vendor",
        "vendor_tax_reg": "123456789",
        "eta_verified": True,
    }

    with patch("app.api.v1.receipts.upload_blob", new_callable=AsyncMock) as mock_upload, \
         patch("app.api.v1.receipts.process_receipt", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = (
            mock_extraction,
            True,
            {"uuid": "abc123", "total": 1200.0, "issuer_rin": "123456789"},
        )
        mock_upload.return_value = "https://r2.example.com/receipts/qr-receipt.jpg"

        image_content = b"\xff\xd8\xff\xe0fake jpeg with qr"
        resp = await auth_client.post(
            "/api/v1/receipts/extract",
            files={"image": ("receipt.jpg", image_content, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["qr_detected"] is True
        assert data["qr_data"]["issuer_rin"] == "123456789"


async def test_receipt_extract_too_large(auth_client, seed_data):
    big_image = b"x" * (10 * 1024 * 1024 + 1)
    resp = await auth_client.post(
        "/api/v1/receipts/extract",
        files={"image": ("receipt.jpg", big_image, "image/jpeg")},
    )
    assert resp.status_code == 413


async def test_receipt_extract_processing_error(auth_client, seed_data):
    with patch("app.api.v1.receipts.upload_blob", new_callable=AsyncMock) as mock_upload, \
         patch("app.api.v1.receipts.process_receipt", new_callable=AsyncMock) as mock_ai:
        mock_ai.side_effect = Exception("AI service unavailable")
        mock_upload.return_value = "https://r2.example.com/receipts/fail.jpg"

        resp = await auth_client.post(
            "/api/v1/receipts/extract",
            files={"image": ("receipt.jpg", b"fake image", "image/jpeg")},
        )
        assert resp.status_code == 422
