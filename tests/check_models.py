import httpx
import os
from dotenv import load_dotenv

load_dotenv()

r = httpx.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"}
)

data = r.json()["data"]

# Filter free models that support vision
vision_keywords = ["vision", "vl", "llava", "gemini", "pixtral", "qwen2-vl", "qwen2.5-vl"]
free_vision = [
    m["id"] for m in data
    if ":free" in m["id"]
    and any(k in m["id"].lower() for k in vision_keywords)
]

print("Free vision models available on your account:")
for m in free_vision:
    print(f"  {m}")

if not free_vision:
    print("No free vision models found.")
    print("\nAll free models available:")
    all_free = [m["id"] for m in data if ":free" in m["id"]]
    for m in all_free:
        print(f"  {m}")