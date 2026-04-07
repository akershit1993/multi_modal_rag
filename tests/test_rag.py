import time
from src.retrieval.rag_chain import RAGChain

rag = RAGChain(top_k=5)

queries = [
    "What are the steps to use the scissor jack safely?",
    "What engine oil grade is recommended for the Kryotec diesel engine?",
    "What does the TPMS warning light on the dashboard mean?"
]

for i, query in enumerate(queries):
    print("\n" + "="*60)
    result = rag.query(query)
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nSources:")
    for s in result['sources']:
        print(f"  page {s['page_number']} | {s['chunk_type']} | similarity {s['similarity']}")

    # Wait between queries to avoid rate limit
    if i < len(queries) - 1:
        print("\nWaiting 10 seconds before next query...")
        time.sleep(10)