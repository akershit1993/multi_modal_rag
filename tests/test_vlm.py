from src.ingestion.parser import PDFParser
from src.models.vlm import VLMProcessor

# Parse PDF
parser = PDFParser()
chunks = parser.parse("sample_documents/harrier-bs6-owners-manual.pdf")

# Get first 2 image chunks only for testing
image_chunks = [c for c in chunks if c.chunk_type == "image"][:2]
print(f"Testing VLM on {len(image_chunks)} images...\n")

# Process through VLM
vlm = VLMProcessor()
for chunk in image_chunks:
    description = vlm.describe_image(chunk.image_data, chunk.page_number)
    print(f"Page {chunk.page_number}:")
    print(f"  {description}")
    print()