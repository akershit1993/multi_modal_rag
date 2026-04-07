from src.ingestion.pipeline import run_ingestion

# Run without VLM first to test embedding + ChromaDB
# We will enable VLM during actual API usage
summary = run_ingestion(
    "sample_documents/harrier-bs6-owners-manual.pdf",
    process_images=False
)

print("\nSummary:")
for key, value in summary.items():
    print(f"  {key}: {value}")