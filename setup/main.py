# ============================================================
# Multimodal RAG API Server - FastAPI Application
# ============================================================
# FastAPI server for the Multimodal RAG system
# Provides REST API endpoints for document processing and querying
# ============================================================

import os
import json
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import RAG components (lazy loading to avoid startup delays)
def get_rag_components():
    """Lazy import of RAG components to avoid startup delays."""
    try:
        from src import MultimodalRAG, RAGSetup
        return MultimodalRAG, RAGSetup
    except ImportError as e:
        logger.error(f"Failed to import RAG components: {e}")
        raise HTTPException(status_code=500, detail="RAG components not available")

# ============================================================
# Setup Logging
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_logs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# Pydantic Models
# ============================================================
class QueryRequest(BaseModel):
    """Request model for queries."""
    question: str

class QueryResponse(BaseModel):
    """Response model for queries."""
    query: str
    answer: str
    context: str
    num_sources: int
    sources: List[Dict[str, Any]]
    timestamp: str

class StatusResponse(BaseModel):
    """Response model for system status."""
    initialized: bool
    data_folder: str
    supported_files: List[str]
    total_documents: int
    timestamp: str

# ============================================================
# Global RAG System Instance (lazy initialized)
# ============================================================
_rag_system = None
_rag_setup = None

# ============================================================
# FastAPI Application
# ============================================================
app = FastAPI(
    title=os.getenv("APP_TITLE", "Multimodal RAG API"),
    description=os.getenv("APP_DESCRIPTION", "REST API for Multimodal Retrieval-Augmented Generation system"),
    version=os.getenv("APP_VERSION", "1.0.0"),
    debug=os.getenv("DEBUG", "false").lower() == "true"
)

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Multimodal RAG API Server", "status": "running"}

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get system status."""
    try:
        global _rag_setup
        if _rag_setup is None:
            MultimodalRAG, RAGSetup = get_rag_components()
            _rag_setup = RAGSetup()

        supported_files = _rag_setup.get_supported_files()
        total_docs = len(supported_files)

        initialized = _rag_system is not None and getattr(_rag_system, 'answer_generator', None) is not None
        status = StatusResponse(
            initialized=initialized,
            data_folder=str(_rag_setup.data_folder),
            supported_files=supported_files,
            total_documents=total_docs,
            timestamp=datetime.now().isoformat()
        )
        return status
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/initialize")
async def initialize_system(background_tasks: BackgroundTasks):
    """Initialize the RAG system."""
    global _rag_system

    try:
        if _rag_system is not None:
            return {"message": "RAG system already initialized"}

        logger.info("Starting RAG system initialization...")

        # Initialize in background to avoid blocking
        background_tasks.add_task(initialize_rag_system)

        return {"message": "RAG system initialization started in background"}

    except Exception as e:
        logger.error(f"Error initializing system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload documents to the data folder."""
    try:
        global _rag_setup
        if _rag_setup is None:
            MultimodalRAG, RAGSetup = get_rag_components()
            _rag_setup = RAGSetup()

        uploaded_files = []

        for file in files:
            # Validate file extension
            supported_extensions = ('.pdf', '.docx', '.pptx', '.xlsx', '.html', '.xml', '.txt', '.md')
            if not file.filename.lower().endswith(supported_extensions):
                continue

            # Save file to data folder
            file_path = _rag_setup.data_folder / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            uploaded_files.append(file.filename)
            logger.info(f"Uploaded file: {file.filename}")

        if not uploaded_files:
            raise HTTPException(status_code=400, detail="No supported files uploaded")

        return {
            "message": f"Successfully uploaded {len(uploaded_files)} files",
            "files": uploaded_files
        }

    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_system(request: QueryRequest):
    """Query the RAG system."""
    global _rag_system

    try:
        if _rag_system is None:
            raise HTTPException(status_code=400, detail="RAG system not initialized. Call /initialize first.")

        logger.info(f"Processing query: {request.question}")

        # Query the system
        try:
            result = _rag_system.query(request.question)
        except Exception as query_error:
            logger.error(f"Query execution error: {query_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Query execution failed: {str(query_error)}")

        if result is None:
            error_msg = "Failed to process query: result is None"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Check if we have any sources
        if result['num_sources'] == 0:
            logger.warning(f"No sources found for query: {request.question}")
            warning_detail = "No matching documents found in database. Please upload documents and reinitialize."
            raise HTTPException(status_code=404, detail=warning_detail)

        # Format response
        response = QueryResponse(
            query=result['query'],
            answer="Based on the retrieved context, here's the relevant information.",  # Placeholder - enhance with LLM
            context=result['context'],
            num_sources=result['num_sources'],
            sources=result['sources'],
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"Query successful. Found {result['num_sources']} sources.")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/reinitialize")
async def reinitialize_system(background_tasks: BackgroundTasks):
    """Reinitialize the RAG system (useful after uploading new documents)."""
    global _rag_system

    try:
        _rag_system = None  # Reset system
        logger.info("RAG system reset. Starting reinitialization...")

        # Reinitialize in background
        background_tasks.add_task(initialize_rag_system)

        return {"message": "RAG system reinitialization started in background"}

    except Exception as e:
        logger.error(f"Error reinitializing system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# Background Tasks
# ============================================================

def initialize_rag_system():
    """Background task to initialize the RAG system."""
    global _rag_system, _rag_setup

    try:
        logger.info("Initializing RAG system in background...")
        MultimodalRAG, RAGSetup = get_rag_components()

        if _rag_setup is None:
            _rag_setup = RAGSetup(data_folder="data")

        _rag_system = MultimodalRAG(data_folder=str(_rag_setup.data_folder))
        _rag_system.initialize()
        logger.info("RAG system initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        logger.error(traceback.format_exc())
        _rag_system = None

# ============================================================
# Error Handlers
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# ============================================================
# Startup and Shutdown Events
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Starting Multimodal RAG API Server...")
    # Data folder will be created lazily when needed

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Multimodal RAG API Server...")

# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info")
    )
