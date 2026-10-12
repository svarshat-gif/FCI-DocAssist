from embeddings.embedder import get_embedder
from rag.vector_store import get_vector_store, RetrievedChunk


class Retriever:
    def __init__(self, db) -> None:
        self.embedder = get_embedder()
        self.vector_store = get_vector_store(db)

    def retrieve(
        self,
        question: str,
        collection_name: str | None = None,
        limit: int = 6,
    ) -> list[RetrievedChunk]:
        if self.vector_store.count(collection_name) == 0:
            return []
        query_embedding = self.embedder.embed_query(question)
        return self.vector_store.query(
            query_embedding=query_embedding,
            collection_name=collection_name,
            limit=limit,
        )
