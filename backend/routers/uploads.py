from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from datetime import datetime, timezone
from models.circular import UploadSession

from api.dependencies import DbSession, get_current_user
from models.schemas import UploadSessionRead
from models.user import User
from services.upload_service import UploadService
from utils.config import get_settings

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("/{session_id}", response_model=UploadSessionRead)
def get_upload_session(session_id: str, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    session = db.get(UploadSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Upload session not found.")
    if session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Upload session expired. Upload the PDF again.")
    return session


@router.post("/pdf", response_model=UploadSessionRead)
def upload_pdf(
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    allow_google_processing: bool = Form(default=False),
) -> UploadSessionRead:
    settings = get_settings()
    if (settings.embedding_provider == "gemini" or settings.llm_provider == "gemini") and not allow_google_processing:
        raise HTTPException(status_code=400, detail="Please consent to Google processing the document before uploading.")
    try:
        return UploadService(db).create_session(file, user)
    finally:
        file.file.close()


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload_session(
    session_id: str,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    UploadService(db).delete_session(session_id, user)
