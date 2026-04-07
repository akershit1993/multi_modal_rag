"""
PDF Parser for Tata Harrier BS6 service manuals.
Extracts text, tables, and images as separate chunk types.
"""

import fitz  # PyMuPDF
import base64
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentChunk:
    """Represents a single extracted chunk from a PDF."""
    chunk_type: str        # "text", "table", or "image"
    content: str           # text content or image description placeholder
    page_number: int       # page where chunk was found
    filename: str          # source PDF filename
    image_data: Optional[str] = None  # base64 encoded image (only for images)


class PDFParser:
    """
    Parses PDF documents and extracts text, table, and image chunks.
    Uses PyMuPDF (fitz) for extraction.
    """

    def __init__(self, min_text_length: int = 50):
        """
        Args:
            min_text_length: Minimum characters for a text block to be kept.
                           Filters out headers, page numbers etc.
        """
        self.min_text_length = min_text_length

    def parse(self, pdf_path: str) -> list[DocumentChunk]:
        """
        Main method — parses a PDF and returns all chunks.

        Args:
            pdf_path: Full path to the PDF file.

        Returns:
            List of DocumentChunk objects (text + table + image chunks).
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        filename = pdf_path.name
        chunks = []

        doc = fitz.open(str(pdf_path))

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Extract text chunks
            text_chunks = self._extract_text(page, page_num + 1, filename)
            chunks.extend(text_chunks)

            # Extract table chunks
            table_chunks = self._extract_tables(page, page_num + 1, filename)
            chunks.extend(table_chunks)

            # Extract image chunks
            image_chunks = self._extract_images(doc, page, page_num + 1, filename)
            chunks.extend(image_chunks)

        doc.close()

        print(f"Parsed '{filename}': {len(chunks)} total chunks")
        print(f"  Text: {sum(1 for c in chunks if c.chunk_type == 'text')}")
        print(f"  Tables: {sum(1 for c in chunks if c.chunk_type == 'table')}")
        print(f"  Images: {sum(1 for c in chunks if c.chunk_type == 'image')}")

        return chunks

    def _extract_text(
        self, page: fitz.Page, page_num: int, filename: str
    ) -> list[DocumentChunk]:
        """
        Extracts text blocks from a page.
        Filters out very short blocks (headers, page numbers).
        """
        chunks = []
        blocks = page.get_text("blocks")

        for block in blocks:
            # block format: (x0, y0, x1, y1, text, block_no, block_type)
            # block_type 0 = text, 1 = image
            if block[6] == 0:  # text block
                text = block[4].strip()
                if len(text) >= self.min_text_length:
                    chunks.append(DocumentChunk(
                        chunk_type="text",
                        content=text,
                        page_number=page_num,
                        filename=filename
                    ))

        return chunks

    def _extract_tables(
        self, page: fitz.Page, page_num: int, filename: str
    ) -> list[DocumentChunk]:
        """
        Extracts tables from a page using PyMuPDF's table detection.
        Converts table to plain text format for embedding.
        """
        chunks = []

        try:
            tables = page.find_tables()
            for table in tables:
                df = table.to_pandas()
                if df.empty:
                    continue

                # Convert table to readable text format
                table_text = df.to_string(index=False)

                if len(table_text.strip()) >= self.min_text_length:
                    chunks.append(DocumentChunk(
                        chunk_type="table",
                        content=table_text,
                        page_number=page_num,
                        filename=filename
                    ))
        except Exception as e:
            print(f"  Warning: Table extraction failed on page {page_num}: {e}")

        return chunks

    def _extract_images(
        self,
        doc: fitz.Document,
        page: fitz.Page,
        page_num: int,
        filename: str
    ) -> list[DocumentChunk]:
        """
        Extracts images from a page and encodes them as base64.
        Image content will later be processed by VLM to generate descriptions.
        """
        chunks = []
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            xref = img[0]  # image reference number

            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Skip very small images (icons, bullets, decorations)
                if len(image_bytes) < 5000:
                    continue

                # Encode image as base64 for VLM processing
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")

                chunks.append(DocumentChunk(
                    chunk_type="image",
                    content=f"[Image on page {page_num} — awaiting VLM description]",
                    page_number=page_num,
                    filename=filename,
                    image_data=f"data:image/{image_ext};base64,{image_b64}"
                ))

            except Exception as e:
                print(f"  Warning: Image extraction failed on page {page_num}, "
                      f"image {img_index}: {e}")

        return chunks