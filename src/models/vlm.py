"""
VLM wrapper for Tata Harrier BS6 image processing via OpenRouter.
"""

import os
import httpx
import base64
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv()


class VLMProcessor:
    """Processes PDF images through VLM to generate text descriptions."""

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = "nvidia/nemotron-nano-12b-v2-vl:free"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")

    def _compress_image(self, image_data: str) -> str:
        """
        Compresses image to reduce size before sending to VLM.
        Resizes to max 512x512 and converts to JPEG at 60% quality.
        This keeps requests within free tier limits.
        """
        # Strip the data:image/...;base64, prefix
        header, b64data = image_data.split(",", 1)
        img_bytes = base64.b64decode(b64data)

        # Open and resize
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((512, 512))

        # Re-encode as compressed JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=60)
        compressed_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return f"data:image/jpeg;base64,{compressed_b64}"

    def describe_image(self, image_data: str, page_number: int) -> str:
        """
        Sends image to VLM and returns text description.

        Args:
            image_data: Base64 encoded image string
            page_number: Page number for context

        Returns:
            Text description of the image.
        """
        try:
            # Compress image first to stay within free tier limits
            compressed = self._compress_image(image_data)

            response = httpx.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": compressed}
                                },
                                {
                                    "type": "text",
                                    "text": (
                                        f"Tata Harrier BS6 manual page {page_number}. "
                                        f"Describe this image briefly: component names, "
                                        f"locations, symbols, or diagram details visible."
                                    )
                                }
                            ]
                        }
                    ],
                    "max_tokens": 150
                },
                timeout=30.0
            )

            
            response.raise_for_status()
            result = response.json()

            # Safely extract content
            choices = result.get("choices", [])
            if not choices:
                return f"[Image page {page_number} — empty response]"

            message = choices[0].get("message", {})
            content = message.get("content", None)

            if not content:
                # Some models return content in parts
                parts = message.get("content_parts", [])
                if parts:
                    content = " ".join(p.get("text", "") for p in parts)

            if not content:
                print(f"\n    Full response: {str(result)[:300]}")
                return f"[Image page {page_number} — no content in response]"

            return content.strip()
            

        except httpx.TimeoutException:
            return f"[Image page {page_number} — timeout]"
        except httpx.HTTPStatusError as e:
            # Print full error for debugging
            print(f"\n    API error detail: {e.response.text[:200]}")
            return f"[Image page {page_number} — error {e.response.status_code}]"
        except Exception as e:
            return f"[Image page {page_number} — failed: {str(e)[:80]}]"

    def process_chunks(self, chunks: list) -> list:
        """
        Processes all image chunks and replaces placeholders with VLM descriptions.
        Skips already-described chunks.
        """
        image_chunks = [c for c in chunks if c.chunk_type == "image"]
        total = len(image_chunks)

        if total == 0:
            print("No image chunks to process.")
            return chunks

        print(f"Processing {total} images through VLM...")

        for i, chunk in enumerate(image_chunks):
            print(f"  [{i+1}/{total}] page {chunk.page_number}...", end=" ")

            if chunk.image_data is None:
                print("skipped")
                continue

            description = self.describe_image(chunk.image_data, chunk.page_number)
            chunk.content = description
            chunk.image_data = None  # free memory
            print("done")

        print("VLM processing complete.")
        return chunks