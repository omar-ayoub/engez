from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.deps import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/uploads", tags=["uploads"])

CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webm": "audio/webm",
    ".mp4": "audio/mp4",
}


@router.get("/{file_path:path}")
async def serve_upload(
    file_path: str,
    user: User = Depends(get_current_active_user),
):
    safe_path = Path(settings.UPLOAD_DIR) / file_path
    # Prevent path traversal
    try:
        safe_path = safe_path.resolve()
        upload_root = Path(settings.UPLOAD_DIR).resolve()
        if not str(safe_path).startswith(str(upload_root)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    except (ValueError, OSError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")

    if not safe_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    media_type = CONTENT_TYPES.get(safe_path.suffix.lower(), "application/octet-stream")
    return FileResponse(safe_path, media_type=media_type)
