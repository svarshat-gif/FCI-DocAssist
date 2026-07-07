from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse

from api.dependencies import DbSession, get_optional_user
from models.schemas import ChatRequest, ChatResponse, ConversationRead, MessageRead
from models.user import User
from services.chat_service import ChatService
from services.export_service import ExportService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: DbSession,
    user: Annotated[User | None, Depends(get_optional_user)],
) -> ChatResponse:
    return ChatService(db).answer(payload, user)


@router.post("/stream")
def chat_stream(
    payload: ChatRequest,
    db: DbSession,
    user: Annotated[User | None, Depends(get_optional_user)],
) -> StreamingResponse:
    response = ChatService(db).answer(payload, user)

    async def events():
        for word in response.answer.split(" "):
            yield f"data: {word} \n\n"
        yield f"event: citations\ndata: {response.model_dump_json()}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/conversations", response_model=list[ConversationRead])
def conversations(
    db: DbSession,
    user: Annotated[User | None, Depends(get_optional_user)],
) -> list:
    return ChatService(db).list_conversations(user)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
def messages(
    conversation_id: str,
    db: DbSession,
    user: Annotated[User | None, Depends(get_optional_user)],
) -> list:
    return ChatService(db).messages(conversation_id, user)


@router.delete("/history")
def clear_history(
    db: DbSession,
    user: Annotated[User | None, Depends(get_optional_user)],
) -> dict[str, int]:
    count = ChatService(db).clear_history(user)
    return {"deleted": count}


@router.get("/conversations/{conversation_id}/export")
def export_conversation(
    conversation_id: str,
    db: DbSession,
    user: Annotated[User | None, Depends(get_optional_user)],
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
