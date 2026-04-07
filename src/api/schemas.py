"""
Pydantic request/response models for Tata Harrier BS6 RAG API.
Defines strict data contracts for all endpoints.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── /ingest ──────────────────────────────────────────────
class IngestResponse(BaseModel):
    message: str
    filename: str
    total_chunks: int
    text_chunks: int
    table_chunks: int
    image_chunks: int
    chunks_indexed: int
    total_indexed: int
    processing_time_seconds: float


# ── /query ───────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5


class SourceReference(BaseModel):
    filename: str
    page_number: int
    chunk_type: str
    similarity: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceReference]
    chunks_retrieved: int


# ── /health ──────────────────────────────────────────────
class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str
    model_llm: str
    model_vlm: str
    model_embedding: str
    chunks_indexed: int
    uptime_seconds: float
    timestamp: str