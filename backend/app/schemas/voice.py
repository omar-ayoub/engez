from pydantic import BaseModel


class VoiceExtractionConfidence(BaseModel):
    amount: float | None = None
    currency: float | None = None
    category: float | None = None
    vendor: float | None = None
    items: float | None = None
    project_hint: float | None = None


class VoiceExtraction(BaseModel):
    amount: float | None = None
    currency: str = "EGP"
    category: str | None = None
    vendor: str | None = None
    items: str | None = None
    project_hint: str | None = None
    confidence: VoiceExtractionConfidence | None = None


class VoiceExtractionResponse(BaseModel):
    transcript: str | None = None
    extraction: VoiceExtraction | None = None
    voice_url: str | None = None
