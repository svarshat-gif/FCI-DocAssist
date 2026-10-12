"""Prepare a bounded batch of existing circulars for PostgreSQL document search."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import exists, select

from database.init_db import init_db
from database.session import SessionLocal
from embeddings.embedder import get_embedder
from models.circular import Circular, CircularChunk
from models.document_vector import DocumentVector
from rag.postgres_store import PostgresVectorStore
from utils.config import get_settings
from utils.text import chunk_pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    settings = get_settings()
    if settings.vector_store != "postgres" or settings.embedding_provider != "gemini":
        raise SystemExit("Set VECTOR_STORE=postgres and EMBEDDING_PROVIDER=gemini first.")
    if not 1 <= args.limit <= 100:
        raise SystemExit("Limit must be between 1 and 100.")
    init_db()
    prepared = 0
    with SessionLocal() as db:
        store = PostgresVectorStore(db)
        ready = exists().where(
            DocumentVector.id == Circular.id + ":0",
            DocumentVector.embedding_model == store.model,
            DocumentVector.collection_name == settings.chroma_collection,
        )
        circulars = db.scalars(select(Circular).where(~ready).order_by(Circular.created_at.desc()).limit(args.limit)).all()
        for circular in circulars:
            originals = db.scalars(select(CircularChunk).where(CircularChunk.circular_id == circular.id).order_by(CircularChunk.chunk_index)).all()
            chunks = chunk_pages([(chunk.page_number, chunk.text) for chunk in originals], max_words=180, overlap_words=30, max_chars=1800)
            if not chunks or len(chunks) > settings.max_document_chunks:
                print(f"Skipped document {circular.id}: empty or exceeds configured text limit.")
                continue
            embeddings = get_embedder().embed_documents([chunk.text for chunk in chunks])
            store.upsert_circular_chunks(circular, chunks, embeddings)
            db.commit()
            prepared += 1
    print(f"Prepared {prepared} existing documents. Repeat to process another batch.")


if __name__ == "__main__":
    main()
