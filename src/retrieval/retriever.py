"""
Retriever for Tata Harrier BS6 RAG system.
Searches ChromaDB for relevant chunks given a query embedding.
"""

from src.retrieval.vector_store import VectorStore
from src.ingestion.embedder import Embedder


class Retriever:
    """
    Retrieves most relevant chunks from ChromaDB
    for a given user query.
    """

    def __init__(self, top_k: int = 5):
        """
        Args:
            top_k: Number of chunks to retrieve per query.
        """
        self.top_k = top_k
        self.store = VectorStore()
        self.embedder = Embedder()

    def retrieve(self, query: str) -> list[dict]:
        """
        Retrieves top-K relevant chunks for a query.

        Args:
            query: User question string

        Returns:
            List of dicts with content, metadata, and similarity score.
        """
        if self.store.count() == 0:
            raise ValueError("Vector store is empty. Please ingest a PDF first.")

        # Embed the query
        query_embedding = self.embedder.embed_query(query)

        # Search ChromaDB
        results = self.store.collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        chunks = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            chunks.append({
                "content": doc,
                "chunk_type": meta.get("chunk_type", "unknown"),
                "page_number": meta.get("page_number", 0),
                "filename": meta.get("filename", "unknown"),
                "similarity": round(1 - dist, 4)
            })

        return chunks