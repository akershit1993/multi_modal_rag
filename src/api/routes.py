"""
FastAPI route definitions for Tata Harrier BS6 RAG API.
Implements /health, /ingest, and /query endpoints.
"""

import os
import time
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from dotenv import load_dotenv

from src.api.schemas import (
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceReference,
    HealthResponse
)
from src.ingestion.pipeline import run_ingestion
from src.retrieval.rag_chain import RAGChain
from src.retrieval.vector_store import VectorStore

load_dotenv()

router = APIRouter()

# Track server start time for uptime calculation
START_TIME = time.time()

# Single RAGChain instance (loaded once, reused for all queries)
_rag_chain: RAGChain = None


def get_rag_chain(force_reload: bool = False) -> RAGChain:
    """Returns cached RAGChain instance, creates if not exists."""
    global _rag_chain
    if _rag_chain is None or force_reload:
        _rag_chain = RAGChain(top_k=5)
    return _rag_chain


# ── GET /health ───────────────────────────────────────────
@router.get("/health", response_model=HealthResponse)
def health_check():
    """
    Returns system status including model info,
    indexed document count, and server uptime.
    """
    store = VectorStore()
    uptime = round(time.time() - START_TIME, 2)

    return HealthResponse(
        status="ok",
        model_llm=os.getenv("LLM_MODEL", "google/gemma-3-27b-it:free"),
        model_vlm=os.getenv("VLM_MODEL", "nvidia/nemotron-nano-12b-v2-vl:free"),
        model_embedding=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        chunks_indexed=store.count(),
        uptime_seconds=uptime,
        timestamp=datetime.utcnow().isoformat()
    )


# ── POST /ingest ──────────────────────────────────────────
@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """
    Accepts a PDF file upload, parses it (text + tables + images),
    embeds all chunks, and stores in ChromaDB vector index.
    Returns ingestion summary with chunk counts and processing time.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted."
        )

    # Save uploaded file to sample_documents/
    save_path = f"sample_documents/{file.filename}"
    start_time = time.time()

    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )

    # Run ingestion pipeline (skip VLM for speed — images get placeholders)
    try:
        summary = run_ingestion(save_path, process_images=False)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )

    processing_time = round(time.time() - start_time, 2)

    # Reset cached RAG chain so it picks up new chunks
    global _rag_chain
    _rag_chain = None

    return IngestResponse(
        message="PDF ingested successfully.",
        filename=file.filename,
        total_chunks=summary["total_chunks"],
        text_chunks=summary["text_chunks"],
        table_chunks=summary["table_chunks"],
        image_chunks=summary["image_chunks"],
        chunks_indexed=summary["chunks_indexed"],
        total_indexed=summary["total_indexed"],
        processing_time_seconds=processing_time
    )


# ── POST /query ───────────────────────────────────────────
@router.post("/query", response_model=QueryResponse)
def query_document(request: QueryRequest):
    """
    Accepts a natural language question, retrieves relevant chunks,
    generates a grounded answer via LLM, and returns answer with sources.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:
        rag = get_rag_chain()
        rag.retriever.top_k = request.top_k
        result = rag.query(request.question)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )

    sources = [
        SourceReference(
            filename=s["filename"],
            page_number=s["page_number"],
            chunk_type=s["chunk_type"],
            similarity=s["similarity"]
        )
        for s in result["sources"]
    ]

    return QueryResponse(
        question=request.question,
        answer=result["answer"],
        sources=sources,
        chunks_retrieved=len(sources)
    )