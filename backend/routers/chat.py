from typing import Annotated, Literal
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse

from api.dependencies import DbSession, get_current_user
from models.schemas import ChatRequest, ChatResponse, ConversationRead, MessageRead
from models.user import User
from services.chat_service import ChatService
from services.export_service import ExportService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> ChatResponse:
    return ChatService(db).answer(payload, user)


@router.post("/stream")
def chat_stream(
    payload: ChatRequest,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    response = ChatService(db).answer(payload, user)

    def events():
        # Validate grounding before sending any generated text to the browser.
        yield json.dumps({"type": "sources", "citations": [item.model_dump(mode="json") for item in response.citations]}) + "\n"
        for offset in range(0, len(response.answer), 48):
            yield json.dumps({"type": "delta", "text": response.answer[offset:offset + 48]}) + "\n"
        yield json.dumps({"type": "done", "response": response.model_dump(mode="json")}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.get("/conversations", response_model=list[ConversationRead])
def conversations(
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    query: str | None = Query(default=None, max_length=200),
) -> list:
    return ChatService(db).list_conversations(user, limit=limit, offset=offset, query=query)


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def conversation(conversation_id: str, db: DbSession, user: Annotated[User, Depends(get_current_user)]):
    return ChatService(db).get_conversation(conversation_id, user)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
def messages(
    conversation_id: str,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> list:
    return ChatService(db).messages(conversation_id, user)


@router.delete("/history")
def clear_history(
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, int]:
    count = ChatService(db).clear_history(user)
    return {"deleted": count}


@router.get("/conversations/{conversation_id}/export")
def export_conversation(
    conversation_id: str,
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
    file_format: Literal["pdf", "txt"] = Query(default="pdf", alias="format"),
) -> Response:
    service = ExportService(db)
    if file_format == "txt":
        data = service.export_txt(conversation_id, user)
        return Response(
            content=data,
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{conversation_id}.txt"'
            },
        )
    data = service.export_pdf(conversation_id, user)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{conversation_id}.pdf"'},
    )
