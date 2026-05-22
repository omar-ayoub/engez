import asyncio
import io
import logging
import uuid
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_BLOB_SIZE = 10 * 1024 * 1024


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


async def upload_blob(
    company_id: str,
    blob_type: str,
    data: bytes,
    extension: str,
) -> str:
    if len(data) > MAX_BLOB_SIZE:
        raise ValueError(f"File exceeds {MAX_BLOB_SIZE // (1024 * 1024)}MB limit")

    if not settings.R2_ACCOUNT_ID or not settings.R2_ACCESS_KEY:
        logger.warning("R2 not configured — skipping upload for %s/%s", company_id, blob_type)
        return f"local://{company_id}/{blob_type}/{uuid.uuid4()}.{extension}"

    now = datetime.utcnow()
    key = f"{company_id}/{blob_type}/{now.strftime('%Y-%m')}/{uuid.uuid4()}.{extension}"
    content_type = _content_type_for(extension)

    await asyncio.to_thread(_sync_upload, data, key, content_type)
    logger.info("Uploaded blob to R2: %s (%d bytes)", key, len(data))
    return f"{settings.R2_PUBLIC_URL}/{key}"


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


async def refresh_receipt_signed_url(receipt_url: str | None, expires_seconds: int = 3600) -> tuple[str, int] | None:
    if not receipt_url:
        return None
    if not settings.R2_ACCOUNT_ID or not settings.R2_ACCESS_KEY or not settings.R2_SECRET_KEY:
        logger.warning("R2 not configured, cannot refresh signed URL")
        return None
    key = extract_r2_key_from_url(receipt_url)
    if not key:
        return None
    signed = await asyncio.to_thread(generate_signed_url, key, expires_seconds)
    return (signed, expires_seconds)
