import sys
sys.path.insert(0, '.')

from src.ingestion.parser import PDFParser

parser = PDFParser()
chunks = parser.parse("sample_documents/nexon-2025-owners-manual.pdf")

print("\nFirst text chunk:")
print(chunks[0].content[:300])

print("\nFirst table chunk (if any):")
tables = [c for c in chunks if c.chunk_type == "table"]
if tables:
    print(tables[0].content[:300])

print("\nFirst image chunk (if any):")
images = [c for c in chunks if c.chunk_type == "image"]
if images:
    print(f"Image found on page {images[0].page_number}")
    print(f"Base64 length: {len(images[0].image_data)} chars")