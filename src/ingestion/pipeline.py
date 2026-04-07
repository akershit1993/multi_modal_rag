"""
Full ingestion pipeline for Tata Harrier BS6 RAG system.
Orchestrates: PDF parsing → VLM image processing → embedding → ChromaDB storage.
"""

from src.ingestion.parser import PDFParser
from src.models.vlm import VLMProcessor
from src.ingestion.embedder import Embedder
from src.retrieval.vector_store import VectorStore


def run_ingestion(pdf_path: str, process_images: bool = True) -> dict:
    """
    Runs the full ingestion pipeline on a PDF file.

    Args:
        pdf_path: Path to the PDF file
        process_images: Whether to run VLM on images (set False for testing)

    Returns:
        Dictionary with ingestion summary stats.
    """
    print(f"\n{'='*50}")
    print(f"Starting ingestion: {pdf_path}")
    print(f"{'='*50}\n")

    # Step 1 — Parse PDF
    print("Step 1: Parsing PDF...")
    parser = PDFParser()
    chunks = parser.parse(pdf_path)

    # Step 2 — Process images through VLM
    if process_images:
        print("\nStep 2: Processing images through VLM...")
        vlm = VLMProcessor()
        # Process first 20 images only to stay within free tier limits
        image_chunks = [c for c in chunks if c.chunk_type == "image"][:20]
        non_image_chunks = [c for c in chunks if c.chunk_type != "image"]
        remaining_images = [c for c in chunks if c.chunk_type == "image"][20:]
        processed = vlm.process_chunks(image_chunks)
        chunks = non_image_chunks + processed + remaining_images
    else:
        print("\nStep 2: Skipping VLM (process_images=False)")

    # Step 3 — Generate embeddings
    print("\nStep 3: Generating embeddings...")
    embedder = Embedder()
    embeddings = embedder.embed_chunks(chunks)

    # Step 4 — Store in ChromaDB
    print("\nStep 4: Storing in ChromaDB...")
    store = VectorStore()
    added = store.add_chunks(chunks, embeddings)

    summary = {
        "filename": pdf_path,
        "total_chunks": len(chunks),
        "text_chunks": sum(1 for c in chunks if c.chunk_type == "text"),
        "table_chunks": sum(1 for c in chunks if c.chunk_type == "table"),
        "image_chunks": sum(1 for c in chunks if c.chunk_type == "image"),
        "chunks_indexed": added,
        "total_indexed": store.count()
    }

    print(f"\n{'='*50}")
    print("Ingestion complete!")
    print(f"  Total chunks indexed: {added}")
    print(f"  Total in vector store: {store.count()}")
    print(f"{'='*50}\n")

    return summary