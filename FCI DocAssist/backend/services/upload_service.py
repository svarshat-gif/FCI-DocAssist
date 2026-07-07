import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from embeddings.embedder import get_embedder
from models.circular import UploadSession
from models.user import User
from rag.vector_store import ChromaVectorStore
from utils.config import get_settings
from utils.pdf import extract_pdf_text
from utils.text import chunk_pages


class UploadService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.embedder = get_embedder()
        self.vector_store = ChromaVectorStore()

    async def create_session(
        self,
        file: UploadFile,
        user: User | None = None,
    ) -> UploadSession:
        filename = _sanitize_filename(file.filename or "uploaded.pdf")
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported.",
            )

        data = await file.read()
        if len(data) > self.settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"PDF upload limit is {self.settings.max_upload_mb} MB.",
            )

        try:
            extracted = extract_pdf_text(data)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        chunks = chunk_pages(extracted.pages)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No extractable text was found in the PDF.",
            )

        collection_name = f"upload_{secrets.token_urlsafe(12).replace('-', '_')}"
        embeddings = self.embedder.embed_documents([chunk.text for chunk in chunks])
        self.vector_store.upsert_temp_chunks(collection_name, filename, chunks, embeddings)

        session = UploadSession(
            user_id=user.id if user else None,
            filename=filename,
            collection_name=collection_name,
            page_count=extracted.page_count,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=self.settings.temp_upload_ttl_minutes),
            session_metadata={"chunk_count": len(chunks)},
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired = (
            self.db.query(UploadSession)
            .filter(UploadSession.expires_at <= now)
            .all()
        )
        for session in expired:
            self.vector_store.delete_collection(session.collection_name)
            self.db.delete(session)
        self.db.commit()
        return len(expired)

    def delete_session(self, session_id: str, user: User | None = None) -> None:
        session = self.db.get(UploadSession, session_id)
        if not session:
            return
        if user and session.user_id and session.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot delete this upload session.",
            )
        self.vector_store.delete_collection(session.collection_name)
        self.db.delete(session)
        self.db.commit()


def _sanitize_filename(filename: str) -> str:
    safe = "".join(ch for ch in filename if ch.isalnum() or ch in "._- ")
    safe = safe.strip().replace(" ", "_")
    return safe[:180] or "uploaded.pdf"
