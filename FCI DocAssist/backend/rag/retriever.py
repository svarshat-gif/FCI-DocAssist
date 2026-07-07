from embeddings.embedder import get_embedder
from rag.vector_store import ChromaVectorStore, RetrievedChunk


class Retriever:
    def __init__(self) -> None:
        self.embedder = get_embedder()
        self.vector_store = ChromaVectorStore()

    def retrieve(
        self,
        question: str,
        collection_name: str | None = None,
        limit: int = 6,
    ) -> list[RetrievedChunk]:
        query_embedding = self.embedder.embed_query(question)
        return self.vector_store.query(
            query_embedding=query_embedding,
            collection_name=collection_name,
            limit=limit,
        )
