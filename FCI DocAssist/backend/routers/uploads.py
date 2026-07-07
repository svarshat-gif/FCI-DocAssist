from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from api.dependencies import DbSession, get_optional_user
from models.schemas import UploadSessionRead
from models.user import User
from services.upload_service import UploadService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/pdf", response_model=UploadSessionRead)
async def upload_pdf(
    db: DbSession,
    user: Annotated[User | None, Depends(get_optional_user)],
    file: UploadFile = File(...),
) -> UploadSessionRead:
    return await UploadService(db).create_session(file, user)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload_session(
    session_id: str,
    db: DbSession,
    user: Annotated[User | None, Depends(get_optional_user)],
) -> None:
    UploadService(db).delete_session(session_id, user)
