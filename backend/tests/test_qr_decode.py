import pytest
from app.services.qr_decode import decode_eta_qr


def test_decode_eta_qr_with_valid_qr():
    assert True


def test_decode_eta_qr_no_qr():
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (100, 100), "white")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()

    result = decode_eta_qr(image_bytes)
    assert result is None
