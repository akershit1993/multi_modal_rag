"""
Embedding module for Tata Harrier BS6 RAG system.
Converts text chunks to vectors using sentence-transformers.
"""

import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()


class Embedder:
    """
    Generates embeddings for document chunks using
    sentence-transformers (runs locally, no API key needed).
    """

    def __init__(self):
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print("Embedding model loaded.")

    def embed_chunks(self, chunks: list) -> list:
        """
        Generates embeddings for a list of DocumentChunk objects.

        Args:
            chunks: List of DocumentChunk objects

        Returns:
            List of embedding vectors (same order as input chunks).
        """
        if not chunks:
            return []

        texts = [chunk.content for chunk in chunks]

        print(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            convert_to_numpy=True
        )

        print(f"Embeddings generated — shape: {embeddings.shape}")
        return embeddings.tolist()

    def embed_query(self, query: str) -> list:
        """
        Generates embedding for a single query string.

        Args:
            query: User question string

        Returns:
            Embedding vector as list.
        """
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.tolist()