"""
ChromaDB vector store setup for Tata Harrier BS6 RAG system.
Manages collection creation, storage, and retrieval.
"""

import os
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()


class VectorStore:
    """
    Manages ChromaDB vector store for document chunks.
    Handles collection creation and document storage.
    """

    def __init__(self):
        db_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")

        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name="harrier_manual",
            metadata={"hnsw:space": "cosine"}
        )

        print(f"VectorStore ready — {self.collection.count()} chunks indexed.")

    def add_chunks(self, chunks: list, embeddings: list) -> int:
        """
        Adds chunks and their embeddings to ChromaDB.

        Args:
            chunks: List of DocumentChunk objects
            embeddings: List of embedding vectors (same order as chunks)

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        documents = []
        metadatas = []
        ids = []

        existing = self.collection.count()

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"chunk_{existing + i}"
            documents.append(chunk.content)
            metadatas.append({
                "chunk_type": chunk.chunk_type,
                "page_number": chunk.page_number,
                "filename": chunk.filename
            })
            ids.append(chunk_id)

        # Add in batches of 500 to avoid memory issues
        batch_size = 500
        total_added = 0

        for start in range(0, len(documents), batch_size):
            end = start + batch_size
            self.collection.add(
                documents=documents[start:end],
                embeddings=embeddings[start:end],
                metadatas=metadatas[start:end],
                ids=ids[start:end]
            )
            total_added += len(documents[start:end])
            print(f"  Indexed batch: {total_added}/{len(documents)} chunks")

        return total_added

    def count(self) -> int:
        """Returns total number of chunks in the vector store."""
        return self.collection.count()

    def reset(self):
        """Clears all chunks from the collection."""
        self.client.delete_collection("harrier_manual")
        self.collection = self.client.get_or_create_collection(
            name="harrier_manual",
            metadata={"hnsw:space": "cosine"}
        )
        print("Vector store reset.")