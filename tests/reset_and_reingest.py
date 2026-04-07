from src.retrieval.vector_store import VectorStore
from src.ingestion.pipeline import run_ingestion

# Clear existing index
print("Resetting vector store...")
store = VectorStore()
store.reset()

# Re-ingest with VLM on first 20 images
summary = run_ingestion(
    "sample_documents/harrier-bs6-owners-manual.pdf",
    process_images=True
)

print("\nSummary:")
for key, value in summary.items():
    print(f"  {key}: {value}")