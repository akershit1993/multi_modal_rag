import httpx
import os
from dotenv import load_dotenv

load_dotenv()

r = httpx.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"}
)

data = r.json()["data"]

# Free text models only
free_text = [
    m["id"] for m in data
    if ":free" in m["id"]
    and not any(k in m["id"].lower() for k in ["vision", "vl", "llava"])
]

print("Free text models on your account:")
for m in free_text:
    print(f"  {m}")