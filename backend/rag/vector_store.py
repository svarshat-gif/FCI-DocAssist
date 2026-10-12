from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection

from models.circular import Circular
from models.schemas import Citation
from utils.config import get_settings
from utils.text import snippet


@dataclass
class RetrievedChunk:
    source_id: str
    text: str
    distance: float | None
    circular_id: str | None
    circular_number: str | None
    title: str
    publication_date: date | None
    official_url: str
    page_number: int | None

    def to_citation(self) -> Citation:
        return Citation(
            source_id=self.source_id,
            circular_number=self.circular_number,
            title=self.title,
            publication_date=self.publication_date,
            official_url=self.official_url,
            page_number=self.page_number,
            snippet=snippet(self.text),
        )


class ChromaVectorStore:
    def __init__(self) -> None:
        import chromadb

        self.settings = get_settings()
        self.client = chromadb.PersistentClient(path=self.settings.chroma_path)

    def count(self, collection_name: str | None = None) -> int:
        collection = self.temp_collection(collection_name) if collection_name else self.official_collection()
        return collection.count()

    def official_collection(self) -> Collection:
        return self.client.get_or_create_collection(
            name=self.settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def temp_collection(self, name: str) -> Collection:
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def delete_collection(self, name: str) -> None:
        try:
            self.client.delete_collection(name=name)
        except Exception:
            return

    def upsert_circular_chunks(
        self,
        circular: Circular,
        chunks: list[Any],
        embeddings: list[list[float]],
    ) -> None:
        if not chunks:
            return
        collection = self.official_collection()
        ids = [f"{circular.id}:{index}" for index, _ in enumerate(chunks)]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "source_id": f"SRC-{index + 1}",
                "circular_id": circular.id,
                "circular_number": circular.circular_number or "",
                "title": circular.title,
                "publication_date": (
                    circular.publication_date.isoformat()
                    if circular.publication_date
                    else ""
                ),
                "department": circular.department or "",
                "topic": circular.topic or "",
                "official_url": circular.official_url,
                "page_number": chunk.page_number or 0,
            }
            for index, chunk in enumerate(chunks)
        ]
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def upsert_temp_chunks(
        self,
        collection_name: str,
        filename: str,
        chunks: list[Any],
        embeddings: list[list[float]],
        expires_at=None,
    ) -> None:
        if not chunks:
            return
        collection = self.temp_collection(collection_name)
        ids = [f"{collection_name}:{index}" for index, _ in enumerate(chunks)]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "source_id": f"PDF-{index + 1}",
                "circular_id": "",
                "circular_number": "Uploaded PDF",
                "title": filename,
                "publication_date": "",
                "department": "",
                "topic": "Uploaded PDF",
                "official_url": "temporary-upload",
                "page_number": chunk.page_number or 0,
            }
            for index, chunk in enumerate(chunks)
        ]
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        query_embedding: list[float],
        collection_name: str | None = None,
        limit: int = 6,
    ) -> list[RetrievedChunk]:
        collection = (
            self.temp_collection(collection_name)
            if collection_name
            else self.official_collection()
        )
        count = collection.count()
        if count == 0:
            return []
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(limit, count),
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        chunks: list[RetrievedChunk] = []
        for index, text in enumerate(documents):
            distance = distances[index] if index < len(distances) else None
            if distance is not None and distance > self.settings.retrieval_max_distance:
                continue
            metadata = metadatas[index] or {}
            chunks.append(
                RetrievedChunk(
                    source_id=metadata.get("source_id") or f"SRC-{index + 1}",
                    text=text,
                    distance=distances[index] if index < len(distances) else None,
                    circular_id=metadata.get("circular_id") or None,
                    circular_number=metadata.get("circular_number") or None,
                    title=metadata.get("title") or "Untitled source",
                    publication_date=_parse_date(metadata.get("publication_date")),
                    official_url=metadata.get("official_url") or "",
                    page_number=_parse_page(metadata.get("page_number")),
                )
            )
        return chunks


def _parse_page(value: Any) -> int | None:
    try:
        page = int(value)
    except (TypeError, ValueError):
        return None
    return page or None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def get_vector_store(db):
    if get_settings().vector_store == "postgres":
        from rag.postgres_store import PostgresVectorStore
        return PostgresVectorStore(db)
    return ChromaVectorStore()
