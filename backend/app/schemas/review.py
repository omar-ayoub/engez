from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConfidenceSummarySchema(BaseModel):
    min: float
    all_high: bool
    low_count: int
    fields: dict[str, float] | None = None


class ReviewQueueEmployee(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_ar: str


class ReviewQueueProject(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_ar: str
    code: str


class ReviewQueueItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_version: int
    status: str
    amount: float
    currency: str
    vendor: str | None = None
    employee: ReviewQueueEmployee
    project: ReviewQueueProject | None = None
    capture_mode: str
    created_at: datetime
    eta_verified: bool = False
    confidence_summary: ConfidenceSummarySchema | None = None
    anomaly_count: int = 0
    bulk_eligible: bool = False


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItemSchema]
    total: int
    page: int
    page_size: int
    pages: int
    server_time: datetime


class ETAInfoSchema(BaseModel):
    verified: bool
    uuid: str | None = None
    vendor_tax_reg: str | None = None


class AuditHistoryItemSchema(BaseModel):
    id: str
    action_type: str
    actor_id: str
    field_name: str | None = None
    value_before: dict | None = None
    value_after: dict | None = None
    rejection_reason: str | None = None
    created_at: datetime


class ReviewDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_version: int
    status: str
    amount: float
    currency: str
    vendor: str | None = None
    vendor_tax_reg: str | None = None
    items: str
    notes: str | None = None
    category_id: str | None = None
    project_id: str | None = None
    capture_mode: str
    receipt_url: str | None = None
    voice_transcript: str | None = None
    eta: ETAInfoSchema | None = None
    ai_extraction: dict | None = None
    ai_confidence: dict[str, float] | None = None
    anomaly_flags: dict | None = None
    employee: ReviewQueueEmployee
    audit_history: list[AuditHistoryItemSchema] = []
    created_at: datetime
    updated_at: datetime | None = None


class ReceiptUrlResponse(BaseModel):
    receipt_url: str
    expires_in: int


class ApproveRequest(BaseModel):
    review_version: int


class ApproveResponse(BaseModel):
    id: str
    status: str
    review_version: int
    reviewed_at: datetime
    next_pending_id: str | None = None


class RejectRequest(BaseModel):
    review_version: int
    reason: str = Field(..., min_length=5, max_length=1000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 5:
            raise ValueError("Reason must be at least 5 characters after trimming whitespace")
        return trimmed


class RejectResponse(BaseModel):
    id: str
    status: str
    review_version: int
    rejection_reason: str
    reviewed_at: datetime
    next_pending_id: str | None = None


class CorrectExpenseRequest(BaseModel):
    review_version: int
    field_name: str
    corrected_value: str | float


class CorrectExpenseResponse(BaseModel):
    id: str
    review_version: int
    field_name: str
    value_before: str
    value_after: str
    correction_feedback_created: bool
    correction_feedback_id: str | None = None


class BulkApproveItem(BaseModel):
    id: str
    review_version: int


class BulkApproveRequest(BaseModel):
    items: list[BulkApproveItem] = Field(..., max_length=50)


class BulkSkippedItem(BaseModel):
    id: str
    reason: str


class BulkConflictItem(BaseModel):
    id: str
    reason: str


class BulkApproveResponse(BaseModel):
    bulk_operation_id: str
    approved: int
    approved_ids: list[str]
    skipped: list[BulkSkippedItem]
    conflicts: list[BulkConflictItem]


class ResubmitRequest(BaseModel):
    review_version: int
    changes: dict[str, object] | None = None


class ResubmitResponse(BaseModel):
    id: str
    status: str
    review_version: int


class ConflictErrorResponse(BaseModel):
    detail: str
    detail_en: str
    current_version: int
    current_status: str


class CorrectionFieldMetricSchema(BaseModel):
    field_name: str
    count: int
    rate: float


class DailyCorrectionTrendSchema(BaseModel):
    date: str
    corrections: int
    ai_expenses: int


class AiMetricsResponse(BaseModel):
    total_expenses: int
    total_ai_expenses: int
    total_corrections: int
    correction_rate: float
    corrections_by_field: list[CorrectionFieldMetricSchema]
    daily_trend: list[DailyCorrectionTrendSchema]
