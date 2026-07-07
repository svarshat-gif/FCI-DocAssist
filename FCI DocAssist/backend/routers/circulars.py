from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import DbSession, get_current_user
from crawler.fci_crawler import FciCrawler
from models.schemas import (
    CircularRead,
    CircularSearchResponse,
    CrawlerRunResponse,
    SummaryRequest,
    SummaryResponse,
)
from models.user import User
from services.circular_service import CircularService
from services.summarization_service import SummarizationService

router = APIRouter(prefix="/circulars", tags=["circulars"])


@router.get("", response_model=CircularSearchResponse)
def search_circulars(
    db: DbSession,
    query: str | None = None,
    circular_number: str | None = None,
    department: str | None = None,
    topic: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CircularSearchResponse:
    items, total = CircularService(db).search(
        query=query,
        circular_number=circular_number,
        department=department,
        topic=topic,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return CircularSearchResponse(items=items, total=total)


@router.get("/recent", response_model=list[CircularRead])
def recent_circulars(db: DbSession) -> list:
    return CircularService(db).recent()


@router.post("/summarize", response_model=SummaryResponse)
def summarize(payload: SummaryRequest, db: DbSession) -> SummaryResponse:
    return SummarizationService(db).summarize(payload)


@router.post("/crawl", response_model=CrawlerRunResponse)
def run_crawler(
    db: DbSession,
    _: Annotated[User, Depends(get_current_user)],
) -> CrawlerRunResponse:
    result = FciCrawler(db).run()
    return CrawlerRunResponse(
        discovered=result.discovered,
        indexed=result.indexed,
        skipped=result.skipped,
        errors=result.errors,
    )


@router.post("/{circular_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def bookmark(
    circular_id: str,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    try:
        CircularService(db).add_bookmark(user, circular_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{circular_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def remove_bookmark(
    circular_id: str,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    CircularService(db).remove_bookmark(user, circular_id)


@router.get("/{circular_id}", response_model=CircularRead)
def get_circular(circular_id: str, db: DbSession):
    circular = CircularService(db).get_by_id_or_number(circular_id, None)
    if not circular:
        raise HTTPException(status_code=404, detail="Circular not found.")
    return circular
