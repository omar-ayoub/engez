from pydantic import BaseModel


class ReceiptLineItem(BaseModel):
    description: str
    quantity: float | None = None
    amount: float | None = None


class ReceiptConfidence(BaseModel):
    amount: float | None = None
    currency: float | None = None
    vendor: float | None = None
    date: float | None = None
    category: float | None = None
    items: float | None = None


class ReceiptExtraction(BaseModel):
    amount: float | None = None
    currency: str = "EGP"
    vendor: str | None = None
    vendor_tax_reg: str | None = None
    date: str | None = None
    category: str | None = None
    items: str | None = None
    line_items: list[ReceiptLineItem] = []
    confidence: ReceiptConfidence | None = None


class QRData(BaseModel):
    uuid: str | None = None
    total: float | None = None
    issuer_rin: str | None = None
    datetime: str | None = None


class ReceiptExtractionResponse(BaseModel):
    extraction: ReceiptExtraction | None = None
    qr_detected: bool = False
    qr_data: QRData | None = None
    receipt_url: str | None = None
