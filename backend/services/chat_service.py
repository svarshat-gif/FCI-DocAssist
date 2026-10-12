from __future__ import annotations

from datetime import datetime, timezone
import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.circular import UploadSession
from models.conversation import Conversation, Message
from models.schemas import ChatRequest, ChatResponse, Citation, SUPPORTED_LANGUAGES
from models.user import User
from rag.prompts import answer_prompt
from rag.retriever import Retriever
from rag.vector_store import RetrievedChunk
from services.gemini_service import GeminiService


NOT_FOUND = "I could not find this information in the available FCI circulars."


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._retriever = None
        self._gemini = None

    @property
    def retriever(self):
        if self._retriever is None:
            self._retriever = Retriever(self.db)
        return self._retriever

    @property
    def gemini(self):
        if self._gemini is None:
            self._gemini = GeminiService()
        return self._gemini

    def answer(self, payload: ChatRequest, user: User | None = None) -> ChatResponse:
        if payload.language not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported language.",
            )

        conversation = self._get_or_create_conversation(payload, user)
        collection_name = self._collection_for_payload(payload, user)
        previous = self.db.scalars(
            select(Message).where(Message.conversation_id == conversation.id, Message.role == "user")
            .order_by(Message.created_at.desc()).limit(2)
        ).all()
        retrieval_question = "\n".join([message.content for message in reversed(previous)] + [payload.message])
        chunks = self.retriever.retrieve(
            question=retrieval_question,
            collection_name=collection_name,
            limit=7,
        )

        self._save_message(conversation.id, "user", payload.message, [])
        if not chunks:
            return self._save_not_found(conversation)

        sources = _format_sources(chunks)
        memory = self._format_memory(conversation.id)
        prompt = answer_prompt(
            language=payload.language,
            memory=memory,
            sources=sources,
            question=payload.message,
        )
        data = self.gemini.generate_json(prompt)
        raw_answer = data.get("answer_markdown")
        answer = raw_answer.strip() if isinstance(raw_answer, str) else ""
        found = data.get("found") is True
        used_ids = _coerce_source_ids(data.get("used_source_ids"))

        citations = _citations_for_ids(chunks, used_ids)
        known_ids = {chunk.source_id for chunk in chunks}
        inline_ids = set(re.findall(r"\[(SRC-\d+)\]", answer))
        if not found or not answer or not citations or not set(used_ids).issubset(known_ids) or inline_ids != set(used_ids):
            return self._save_not_found(conversation)

        self._save_message(
            conversation.id,
            "assistant",
            answer,
            [citation.model_dump(mode="json") for citation in citations],
        )
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return ChatResponse(
            conversation_id=conversation.id,
            answer=answer,
            citations=citations,
            found=True,
        )

    def list_conversations(self, user: User | None, limit: int = 50, offset: int = 0, query: str | None = None) -> list[Conversation]:
        stmt = select(Conversation)
        if user:
            stmt = stmt.where(Conversation.user_id == user.id)
        else:
            return []
        if query and query.strip():
            stmt = stmt.where(Conversation.title.icontains(query.strip(), autoescape=True))
        return list(
            self.db.scalars(
                stmt.order_by(Conversation.updated_at.desc(), Conversation.id.desc()).limit(limit).offset(offset)
            ).all()
        )

    def get_conversation(self, conversation_id: str, user: User | None) -> Conversation:
        conversation = self.db.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        if not user or conversation.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied.")
        return conversation

    def messages(self, conversation_id: str, user: User | None) -> list[Message]:
        conversation = self.get_conversation(conversation_id, user)
        return list(
            self.db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            ).all()
        )

    def clear_history(self, user: User | None) -> int:
        if not user:
            return 0
        from services.upload_service import UploadService
        UploadService(self.db).delete_user_sessions(user)
        conversations = list(self.db.scalars(select(Conversation).where(Conversation.user_id == user.id)).all())
        count = len(conversations)
        for conversation in conversations:
            self.db.delete(conversation)
        self.db.commit()
        return count

    def _get_or_create_conversation(
        self,
        payload: ChatRequest,
        user: User | None,
    ) -> Conversation:
        if payload.conversation_id:
            conversation = self.db.get(Conversation, payload.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found.")
            if not user or conversation.user_id != user.id:
                raise HTTPException(status_code=403, detail="Access denied.")
            if conversation.source_mode != payload.source_mode or conversation.upload_session_id != payload.upload_session_id:
                raise HTTPException(status_code=400, detail="Start a new chat to change the document source.")
            return conversation

        title = payload.message.strip()[:70] or "New Chat"
        conversation = Conversation(
            user_id=user.id if user else None,
            title=title,
            language=payload.language,
            source_mode=payload.source_mode,
            upload_session_id=payload.upload_session_id,
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def _collection_for_payload(self, payload: ChatRequest, user: User | None) -> str | None:
        if payload.source_mode == "official":
            return None
        if not payload.upload_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please upload a PDF before asking about it.",
            )
        session = self.db.get(UploadSession, payload.upload_session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Upload session not found.")
        if not user or session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied.")
        if session.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Upload session expired.")
        return session.collection_name

    def _format_memory(self, conversation_id: str) -> str:
        messages = list(
            self.db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(8)
            ).all()
        )
        ordered = list(reversed(messages))
        return "\n".join(f"{message.role}: {message.content}" for message in ordered)

    def _save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict],
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def _save_not_found(self, conversation: Conversation) -> ChatResponse:
        self._save_message(conversation.id, "assistant", NOT_FOUND, [])
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return ChatResponse(
            conversation_id=conversation.id,
            answer=NOT_FOUND,
            citations=[],
            found=False,
        )


def _format_sources(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for index, chunk in enumerate(chunks, start=1):
        source_id = f"SRC-{index}"
        blocks.append(
            "\n".join(
                [
                    f"[{source_id}]",
                    f"Title: {chunk.title}",
                    f"Circular Number: {chunk.circular_number or 'Unknown'}",
                    f"Publication Date: {chunk.publication_date or 'Unknown'}",
                    f"Official URL: {chunk.official_url}",
                    f"Page: {chunk.page_number or 'Unknown'}",
                    f"Excerpt: {chunk.text}",
                ]
            )
        )
        chunk.source_id = source_id
    return "\n\n".join(blocks)


def _coerce_source_ids(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).startswith("SRC-")]
    if isinstance(value, str) and value.startswith("SRC-"):
        return [value]
    return []


def _citations_for_ids(
    chunks: list[RetrievedChunk],
    source_ids: list[str],
) -> list[Citation]:
    by_id = {chunk.source_id: chunk for chunk in chunks}
    citations: list[Citation] = []
    for source_id in source_ids:
        chunk = by_id.get(source_id)
        if chunk:
            citations.append(chunk.to_citation())
    return citations
