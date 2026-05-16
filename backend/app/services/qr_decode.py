import io
import logging
import re
from dataclasses import dataclass

from PIL import Image, ImageEnhance
from pyzbar.pyzbar import decode as pyzbar_decode

logger = logging.getLogger(__name__)


@dataclass
class ETAQRData:
    uuid: str | None = None
    total: float | None = None
    issuer_rin: str | None = None
    datetime: str | None = None
    raw_url: str | None = None


def decode_eta_qr(image_bytes: bytes) -> ETAQRData | None:
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        logger.debug("Failed to open image for QR decoding")
        return None

    decoded = _try_decode(img)
    if not decoded:
        gray = img.convert("L")
        enhanced = ImageEnhance.Contrast(gray).enhance(2.0)
        decoded = _try_decode(enhanced)

    if not decoded:
        return None

    for obj in decoded:
        data = obj.data.decode("utf-8", errors="ignore")
        eta = _parse_eta_url(data)
        if eta:
            logger.info("Decoded ETA QR: uuid=%s", eta.uuid)
            return eta

    return None


def _try_decode(img: Image.Image):
    try:
        return pyzbar_decode(img)
    except Exception:
        return None


def _parse_eta_url(data: str) -> ETAQRData | None:
    pattern = r"receipts/search/([^/\s]+)/share/([^#\s]+)#Total:([^,]+),IssuerRIN:([^,\s]+)"
    match = re.search(pattern, data)
    if not match:
        return None

    uuid_val = match.group(1)
    datetime_val = match.group(2)
    total_str = match.group(3)
    issuer_rin = match.group(4)

    try:
        total = float(total_str)
    except ValueError:
        total = None

    return ETAQRData(
        uuid=uuid_val,
        total=total,
        issuer_rin=issuer_rin,
        datetime=datetime_val,
        raw_url=data,
    )
