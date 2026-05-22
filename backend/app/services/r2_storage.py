import asyncio
import io
import logging
import uuid
from datetime import datetime
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_BLOB_SIZE = 10 * 1024 * 1024


def _r2_configured() -> bool:
    return bool(settings.R2_ACCOUNT_ID and settings.R2_ACCESS_KEY and settings.R2_SECRET_KEY)


# ── R2 helpers ───────────────────────────────────────────────


def _get_s3_client():
    endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.R2_ACCESS_KEY,
        aws_secret_access_key=settings.R2_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
    )


def _sync_upload(data: bytes, key: str, content_type: str) -> None:
    s3 = _get_s3_client()
    s3.upload_fileobj(
        io.BytesIO(data),
        settings.R2_BUCKET,
        key,
        ExtraArgs={"ContentType": content_type},
    )


# ── Local storage helpers ────────────────────────────────────


def _sync_local_write(data: bytes, rel_path: str) -> None:
    dest = Path(settings.UPLOAD_DIR) / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def _local_url(rel_path: str) -> str:
    return f"/api/v1/uploads/{rel_path}"


def _is_local_url(url: str) -> bool:
    return url.startswith("/api/v1/uploads/") or url.startswith("local://")


# ── Public API ───────────────────────────────────────────────


async def upload_blob(
    company_id: str,
    blob_type: str,
    data: bytes,
    extension: str,
) -> str:
    if len(data) > MAX_BLOB_SIZE:
        raise ValueError(f"File exceeds {MAX_BLOB_SIZE // (1024 * 1024)}MB limit")

    now = datetime.utcnow()
    rel_path = f"{company_id}/{blob_type}/{now.strftime('%Y-%m')}/{uuid.uuid4()}.{extension}"

    if not _r2_configured():
        await asyncio.to_thread(_sync_local_write, data, rel_path)
        logger.info("Saved blob locally: %s (%d bytes)", rel_path, len(data))
        return _local_url(rel_path)

    content_type = _content_type_for(extension)
    await asyncio.to_thread(_sync_upload, data, rel_path, content_type)
    logger.info("Uploaded blob to R2: %s (%d bytes)", rel_path, len(data))
    return f"{settings.R2_PUBLIC_URL}/{rel_path}"


def generate_signed_url(key: str, expires_seconds: int = 3600) -> str:
    s3 = _get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET, "Key": key},
        ExpiresIn=expires_seconds,
    )


def _content_type_for(ext: str) -> str:
    mapping = {
        "webm": "audio/webm",
        "mp4": "audio/mp4",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
    }
    return mapping.get(ext.lower(), "application/octet-stream")


def extract_r2_key_from_url(url: str) -> str | None:
    if not url:
        return None
    prefix = f"{settings.R2_PUBLIC_URL}/"
    if url.startswith(prefix):
        return url[len(prefix):]
    if "/" in url:
        return url.split("/", 3)[-1] if url.count("/") >= 3 else None
    return None


def extract_local_path_from_url(url: str) -> str | None:
    prefix = "/api/v1/uploads/"
    if url.startswith(prefix):
        return url[len(prefix):]
    if url.startswith("local://"):
        return url[len("local://"):]
    return None


async def refresh_receipt_signed_url(receipt_url: str | None, expires_seconds: int = 3600) -> tuple[str, int] | None:
    if not receipt_url:
        return None

    # Local files don't need signed URLs — just return the path
    if _is_local_url(receipt_url):
        local_path = extract_local_path_from_url(receipt_url)
        if local_path:
            return (_local_url(local_path), 0)
        return None

    if not _r2_configured():
        logger.warning("R2 not configured, cannot refresh signed URL")
        return None

    key = extract_r2_key_from_url(receipt_url)
    if not key:
        return None
    signed = await asyncio.to_thread(generate_signed_url, key, expires_seconds)
    return (signed, expires_seconds)
