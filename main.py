"""
Tata Nexon Multimodal RAG System
FastAPI application entry point.
"""

import os
# Suppress ONNXRuntime device discovery warnings in container environment
os.environ['ORT_LOGLEVEL_ORT_LOGS'] = '1'
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from src.api.routes import router
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
INTERFACE_PATH = BASE_DIR / "interface.html"

app = FastAPI(
    title="Tata Nexon RAG API",
    description=(
        "Multimodal Retrieval-Augmented Generation system "
        "for Tata Nexon owners manual intelligence. "
        "Supports text, table, and image-based queries."
    ),
    version="1.0.0",
    contact={
        "name": "Tata Nexon API",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "Tata Nexon RAG System is running.",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/ui", include_in_schema=False)
def ui():
    return FileResponse(INTERFACE_PATH)