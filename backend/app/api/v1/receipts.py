import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_tenant_scope
from app.models.user import User
from app.schemas.receipt import ReceiptExtractionResponse
from app.services.ai_receipt import process_receipt
from app.services.r2_storage import upload_blob
from app.services.rate_limiter import check_rate_limit
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/receipts", tags=["receipts"])

MAX_IMAGE_SIZE = 10 * 1024 * 1024


@router.post("/extract", response_model=ReceiptExtractionResponse)
async def extract_receipt(
    image: Annotated[UploadFile, File()],
    company_id: str = Depends(get_tenant_scope),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await check_rate_limit(company_id, "receipt", settings.AI_RATE_LIMIT_RECEIPT)

    if image.size and image.size > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "detail": "ملف الصورة كبير جداً (الحد الأقصى 10 ميجابايت)",
                "detail_en": "Image file too large (max 10MB)",
            },
        )

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "detail": "ملف الصورة كبير جداً (الحد الأقصى 10 ميجابايت)",
                "detail_en": "Image file too large (max 10MB)",
            },
        )

    receipt_url = await upload_blob(company_id, "receipts", image_bytes, "jpg")

    try:
        extraction, qr_detected, qr_data = await process_receipt(
            image_bytes, company_id, db
        )
    except Exception:
        logger.exception("Receipt processing failed for company=%s", company_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "detail": "تعذر قراءة الإيصال. يرجى إعادة التصوير",
                "detail_en": "Could not read receipt. Please retake the photo",
                "extraction": None,
                "qr_detected": False,
                "qr_data": None,
            },
        )

    return ReceiptExtractionResponse(
        extraction=extraction,
        qr_detected=qr_detected,
        qr_data=qr_data,
        receipt_url=receipt_url,
    )
