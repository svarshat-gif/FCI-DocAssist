import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.dependencies import DbSession
from crawler.fci_crawler import CrawlerBusyError, FciCrawler
from models.schemas import CrawlerRunResponse
from services.upload_service import UploadService
from utils.config import get_settings

router = APIRouter(prefix="/maintenance", tags=["maintenance"])
bearer = HTTPBearer(auto_error=False)


@router.post("/update", response_model=CrawlerRunResponse)
def update(db: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    token = get_settings().crawler_job_token
    if not token or len(token) < 32 or not credentials or not secrets.compare_digest(token, credentials.credentials):
        raise HTTPException(status_code=401, detail="Not authorized.")
    UploadService(db).cleanup_expired()
    try:
        result = FciCrawler(db).run()
    except CrawlerBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CrawlerRunResponse(**result.__dict__)
