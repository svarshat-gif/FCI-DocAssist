from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from models.document_vector import DocumentVector
from rag.vector_store import RetrievedChunk, _parse_date, _parse_page
from utils.config import get_settings


class PostgresVectorStore:
    """Keep persistent document search in the same transaction as app records."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        if self.settings.embedding_provider != "gemini":
            raise ValueError("PostgreSQL document search requires EMBEDDING_PROVIDER=gemini.")
        self.model = f"gemini:{self.settings.gemini_embedding_model}:768"

    def _scope(self, collection_name: str | None):
        return (
            DocumentVector.collection_name == (collection_name or self.settings.chroma_collection),
            DocumentVector.embedding_model == self.model,
            or_(DocumentVector.expires_at.is_(None), DocumentVector.expires_at > datetime.now(timezone.utc)),
        )

    def count(self, collection_name: str | None = None) -> int:
        return self.db.scalar(select(func.count()).select_from(DocumentVector).where(*self._scope(collection_name))) or 0

    def delete_collection(self, name: str) -> None:
        self.db.execute(delete(DocumentVector).where(DocumentVector.collection_name == name))

    def _upsert(self, collection, ids, chunks, embeddings, metadata, expires_at=None):
        if len(chunks) != len(embeddings):
            raise ValueError("Document embeddings are incomplete.")
        self.db.execute(delete(DocumentVector).where(DocumentVector.expires_at <= datetime.now(timezone.utc)))
        existing = set(self.db.scalars(select(DocumentVector.id).where(DocumentVector.id.in_(ids))))
        total = self.db.scalar(select(func.count()).select_from(DocumentVector)) or 0
        if total + len(ids) - len(existing) > self.settings.max_stored_chunks:
            raise HTTPException(status_code=507, detail="Document storage is full. Please contact the administrator.")
        for index, chunk in enumerate(chunks):
            vector = self.db.get(DocumentVector, ids[index]) if ids[index] in existing else DocumentVector(id=ids[index])
            vector.collection_name = collection
            vector.embedding_model = self.model
            vector.text = chunk.text
            vector.embedding = embeddings[index]
            vector.source_metadata = metadata[index]
            vector.expires_at = expires_at
            self.db.add(vector)
        self.db.flush()

    def upsert_circular_chunks(self, circular, chunks, embeddings):
        metadata = [{
            "circular_id": circular.id, "circular_number": circular.circular_number,
            "title": circular.title, "publication_date": circular.publication_date.isoformat() if circular.publication_date else None,
            "official_url": circular.official_url, "page_number": chunk.page_number,
        } for chunk in chunks]
        self._upsert(self.settings.chroma_collection, [f"{circular.id}:{i}" for i in range(len(chunks))], chunks, embeddings, metadata)

    def upsert_temp_chunks(self, collection_name, filename, chunks, embeddings, expires_at=None):
        metadata = [{"title": filename, "circular_number": "Uploaded PDF", "official_url": "temporary-upload", "page_number": chunk.page_number} for chunk in chunks]
        self._upsert(collection_name, [f"{collection_name}:{i}" for i in range(len(chunks))], chunks, embeddings, metadata, expires_at)

    def query_statement(self, query_embedding, collection_name=None, limit=6):
        distance = DocumentVector.embedding.cosine_distance(query_embedding).label("distance")
        return select(DocumentVector, distance).where(*self._scope(collection_name), distance <= self.settings.retrieval_max_distance).order_by(distance, DocumentVector.id).limit(limit)

    def query(self, query_embedding, collection_name=None, limit=6):
        rows = self.db.execute(self.query_statement(query_embedding, collection_name, limit)).all()
        result = []
        for index, (vector, distance) in enumerate(rows, start=1):
            metadata = vector.source_metadata
            result.append(RetrievedChunk(
                source_id=f"SRC-{index}", text=vector.text, distance=float(distance),
                circular_id=metadata.get("circular_id"), circular_number=metadata.get("circular_number"),
                title=metadata.get("title") or "Untitled source", publication_date=_parse_date(metadata.get("publication_date")),
                official_url=metadata.get("official_url") or "", page_number=_parse_page(metadata.get("page_number")),
            ))
        return result
