import time
import os
from dotenv import load_dotenv
load_dotenv()

print("Model being used:", os.getenv("LLM_MODEL"))

from src.retrieval.rag_chain import RAGChain

print("Waiting 60 seconds for rate limit to reset...")
time.sleep(60)

rag = RAGChain(top_k=3)
result = rag.query("What engine oil grade is recommended for the Kryotec diesel engine?")
print(f"\nAnswer:\n{result['answer']}")