from fastapi import APIRouter
from utils.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/upload-policy")
def upload_policy():
    settings = get_settings()
    return {"google_processing": settings.embedding_provider == "gemini" or settings.llm_provider == "gemini", "max_upload_mb": settings.max_upload_mb, "expires_minutes": settings.temp_upload_ttl_minutes}
