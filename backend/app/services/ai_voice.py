import json
import logging
from io import BytesIO

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.correction import CorrectionFeedback
from app.schemas.voice import VoiceExtraction, VoiceExtractionConfidence

logger = logging.getLogger(__name__)

EGYPTIAN_ARABIC_PROMPT = (
    "أنت مساعد لتحويل الأصوات إلى بيانات مصروفات. "
    "المستخدم يتحدث باللهجة المصرية. "
    "كلمات شائعة: أسمنت، طوب، حديد، رمل، بناء، نقل، بنزين، سولار، "
    "أجور عمال، إيجار، معدات، صيانة، تصاريح. "
    "العملة الافتراضية: جنيه مصري (EGP)."
)

EXTRACTION_SYSTEM_PROMPT = """You are an expense data extraction assistant.
Given an Arabic (Egyptian dialect) voice transcript, extract structured expense data.
Return a JSON object with these fields:
- amount: number or null (never guess)
- currency: string (default "EGP")
- category: one of [materials, transport, fuel, food, equipment, permits, maintenance, other] or null
- vendor: string or null
- items: string description of what was purchased or null
- project_hint: string or null (name of a project mentioned)
- confidence: object with 0-1 scores for each field (amount, currency, category, vendor, items, project_hint)

Use the few-shot examples below to learn the user's correction patterns.
Few-shot examples: {few_shot_examples}

Active project names: {project_names}

Respond ONLY with valid JSON, no markdown."""


async def _get_few_shot_examples(
    company_id: str, db: AsyncSession, limit: int = 10
) -> list[dict]:
    result = await db.execute(
        select(CorrectionFeedback)
        .where(CorrectionFeedback.company_id == company_id)
        .order_by(CorrectionFeedback.created_at.desc())
        .limit(limit)
    )
    feedbacks = result.scalars().all()
    return [
        {
            "field": f.field_name,
            "ai_said": f.ai_value,
            "user_corrected_to": f.corrected_value,
        }
        for f in feedbacks
    ]


async def transcribe_and_extract(
    audio_bytes: bytes,
    company_id: str,
    project_names: list[str],
    db: AsyncSession,
    mime_type: str = "audio/webm",
) -> tuple[str | None, VoiceExtraction | None]:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    audio_file = BytesIO(audio_bytes)
    audio_file.name = "audio.webm" if "webm" in mime_type else "audio.mp4"

    transcription = await client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=audio_file,
        language="ar",
        response_format="text",
        prompt=EGYPTIAN_ARABIC_PROMPT,
    )

    transcript = transcription.strip() if transcription else None

    if not transcript:
        return None, None

    few_shot = await _get_few_shot_examples(company_id, db)
    few_shot_str = json.dumps(few_shot, ensure_ascii=False) if few_shot else "[]"
    project_names_str = ", ".join(project_names) if project_names else "None"

    extraction_response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": EXTRACTION_SYSTEM_PROMPT.format(
                    few_shot_examples=few_shot_str,
                    project_names=project_names_str,
                ),
            },
            {"role": "user", "content": transcript},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw = extraction_response.choices[0].message.content
    try:
        data = json.loads(raw)
        confidence_data = data.get("confidence", {})
        confidence = VoiceExtractionConfidence(
            amount=confidence_data.get("amount"),
            currency=confidence_data.get("currency"),
            category=confidence_data.get("category"),
            vendor=confidence_data.get("vendor"),
            items=confidence_data.get("items"),
            project_hint=confidence_data.get("project_hint"),
        )
        extraction = VoiceExtraction(
            amount=data.get("amount"),
            currency=data.get("currency", "EGP"),
            category=data.get("category"),
            vendor=data.get("vendor"),
            items=data.get("items"),
            project_hint=data.get("project_hint"),
            confidence=confidence,
        )
    except json.JSONDecodeError:
        logger.warning("Failed to parse extraction JSON for company=%s: %s", company_id, raw)
        extraction = None

    return transcript, extraction
