"""
RAG chain for Tata Harrier BS6 system.
Combines retriever + LLM into a single query interface.
"""

from src.retrieval.retriever import Retriever
from src.models.llm import LLMProcessor


class RAGChain:
    """
    End-to-end RAG pipeline.
    Takes a question, retrieves chunks, generates grounded answer.
    """

    def __init__(self, top_k: int = 5):
        self.retriever = Retriever(top_k=top_k)
        self.llm = LLMProcessor()

    def query(self, question: str) -> dict:
        """
        Runs full RAG pipeline for a question.

        Args:
            question: User question string

        Returns:
            Dict with answer and sources.
        """
        print(f"Query: {question}")

        # Retrieve relevant chunks
        chunks = self.retriever.retrieve(question)
        print(f"Retrieved {len(chunks)} chunks:")
        for c in chunks:
            print(f"  [{c['chunk_type']}] page {c['page_number']} "
                  f"(similarity: {c['similarity']})")

        # Generate answer
        result = self.llm.generate(question, chunks)
        return result