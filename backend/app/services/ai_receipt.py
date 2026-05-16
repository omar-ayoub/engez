import asyncio
import base64
import json
import logging

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.vendor_cache import VendorCache
from app.services.qr_decode import decode_eta_qr
from app.schemas.receipt import (
    QRData,
    ReceiptConfidence,
    ReceiptExtraction,
    ReceiptLineItem,
)

logger = logging.getLogger(__name__)

RECEIPT_OCR_PROMPT = """You are a receipt OCR assistant.
Extract data from this receipt image (Arabic or English text).
Return a JSON object with:
- amount: total amount (number or null)
- currency: "EGP" default
- vendor: business name (string or null)
- vendor_tax_reg: tax registration number if visible (string or null)
- date: receipt date in YYYY-MM-DD format (string or null)
- category: one of [materials, transport, fuel, food, equipment, permits, maintenance, other] or null
- items: description of purchased items (string or null)
- line_items: array of {description, quantity, amount} objects
- confidence: object with 0-1 scores for each field (amount, currency, vendor, date, category, items)

Respond ONLY with valid JSON, no markdown."""


async def process_receipt(
    image_bytes: bytes,
    company_id: str,
    db: AsyncSession,
) -> tuple[ReceiptExtraction, bool, QRData | None]:
    # QR decode is CPU-bound — run in thread to avoid blocking event loop
    qr_raw = await asyncio.to_thread(decode_eta_qr, image_bytes)
    qr_detected = qr_raw is not None

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": RECEIPT_OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=1000,
    )

    raw = response.choices[0].message.content
    data = json.loads(raw) if raw else {}

    confidence_data = data.get("confidence", {})
    confidence = ReceiptConfidence(
        amount=confidence_data.get("amount"),
        currency=confidence_data.get("currency"),
        vendor=confidence_data.get("vendor"),
        date=confidence_data.get("date"),
        category=confidence_data.get("category"),
        items=confidence_data.get("items"),
    )

    line_items = [
        ReceiptLineItem(
            description=li.get("description", ""),
            quantity=li.get("quantity"),
            amount=li.get("amount"),
        )
        for li in data.get("line_items", [])
    ]

    extraction = ReceiptExtraction(
        amount=data.get("amount"),
        currency=data.get("currency", "EGP"),
        vendor=data.get("vendor"),
        vendor_tax_reg=data.get("vendor_tax_reg"),
        date=data.get("date"),
        category=data.get("category"),
        items=data.get("items"),
        line_items=line_items,
        confidence=confidence,
    )

    # Convert ETAQRData to QRData schema for response
    qr_data: QRData | None = None
    if qr_raw:
        qr_data = QRData(
            uuid=qr_raw.uuid,
            total=qr_raw.total,
            issuer_rin=qr_raw.issuer_rin,
            datetime=qr_raw.datetime,
        )

        if qr_raw.total is not None:
            extraction.amount = qr_raw.total
        if qr_raw.issuer_rin:
            extraction.vendor_tax_reg = qr_raw.issuer_rin
        if qr_raw.datetime:
            extraction.date = qr_raw.datetime

        if qr_raw.issuer_rin:
            vendor_result = await db.execute(
                select(VendorCache).where(
                    VendorCache.company_id == company_id,
                    VendorCache.tax_registration == qr_raw.issuer_rin,
                )
            )
            vendor = vendor_result.scalar_one_or_none()
            if vendor:
                extraction.vendor = vendor.name_ar or vendor.name
                if vendor.category_hint:
                    extraction.category = vendor.category_hint

    logger.info(
        "Receipt processed for company=%s qr_detected=%s",
        company_id, qr_detected,
    )
    return extraction, qr_detected, qr_data
