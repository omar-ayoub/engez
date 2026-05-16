import pytest
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio


async def test_voice_extract_success(auth_client, seed_data):
    mock_transcript = "مصاريف أسمنت ميتين جنيه لمشروع برج أ"
    mock_extraction = {
        "amount": 200.0,
        "currency": "EGP",
        "category": "materials",
        "vendor": None,
        "items": "أسمنت",
        "project_hint": "برج أ",
        "confidence": {"amount": 0.95, "category": 0.8},
    }

    with patch("app.api.v1.voice.upload_blob", new_callable=AsyncMock) as mock_upload, \
         patch("app.api.v1.voice.transcribe_and_extract", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = (mock_transcript, mock_extraction)
        mock_upload.return_value = "https://r2.example.com/voice/test.webm"

        audio_content = b"fake webm audio data"
        resp = await auth_client.post(
            "/api/v1/voice/extract",
            files={"audio": ("voice.webm", audio_content, "audio/webm")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["transcript"] == mock_transcript
        assert data["extraction"]["amount"] == 200.0
        assert data["voice_url"] is not None


async def test_voice_extract_too_large(auth_client, seed_data):
    big_audio = b"x" * (10 * 1024 * 1024 + 1)
    resp = await auth_client.post(
        "/api/v1/voice/extract",
        files={"audio": ("voice.webm", big_audio, "audio/webm")},
    )
    assert resp.status_code == 413


async def test_voice_extract_empty_audio(auth_client, seed_data):
    with patch("app.api.v1.voice.upload_blob", new_callable=AsyncMock) as mock_upload, \
         patch("app.api.v1.voice.transcribe_and_extract", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = (None, None)
        mock_upload.return_value = "https://r2.example.com/voice/empty.webm"

        resp = await auth_client.post(
            "/api/v1/voice/extract",
            files={"audio": ("voice.webm", b"", "audio/webm")},
        )
        assert resp.status_code == 422
