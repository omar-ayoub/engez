from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_tenant_scope
from app.models.project import Project
from app.models.user import User
from app.schemas.voice import VoiceExtractionResponse
from app.services.ai_voice import transcribe_and_extract
from app.services.r2_storage import upload_blob
from app.services.rate_limiter import check_rate_limit
from app.core.config import settings

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_AUDIO_SIZE = 10 * 1024 * 1024


@router.post("/extract", response_model=VoiceExtractionResponse)
async def extract_voice(
    audio: Annotated[UploadFile, File()],
    company_id: str = Depends(get_tenant_scope),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await check_rate_limit(company_id, "voice", settings.AI_RATE_LIMIT_VOICE)

    if audio.size and audio.size > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "detail": "ملف الصوت كبير جداً (الحد الأقصى 10 ميجابايت)",
                "detail_en": "Audio file too large (max 10MB)",
            },
        )

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "detail": "ملف الصوت كبير جداً (الحد الأقصى 10 ميجابايت)",
                "detail_en": "Audio file too large (max 10MB)",
            },
        )

    ext = "webm" if audio.content_type and "webm" in audio.content_type else "mp4"
    voice_url = await upload_blob(company_id, "voice", audio_bytes, ext)

    projects_result = await db.execute(
        select(Project.name_ar, Project.name).where(
            Project.company_id == company_id, Project.is_active == True
        )
    )
    project_rows = projects_result.all()
    project_names = [r[0] for r in project_rows] + [r[1] for r in project_rows]

    mime_type = audio.content_type or "audio/webm"
    transcript, extraction = await transcribe_and_extract(
        audio_bytes, company_id, project_names, db, mime_type
    )

    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "detail": "تعذر معالجة التسجيل الصوتي",
                "detail_en": "Could not process voice recording",
                "transcript": None,
                "extraction": None,
            },
        )

    return VoiceExtractionResponse(
        transcript=transcript,
        extraction=extraction,
        voice_url=voice_url,
    )
