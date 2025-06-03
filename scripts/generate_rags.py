from pathlib import Path

from rag.rag import StatuteRAG
from statute.statutecache import StatuteCache

CACHE_PATH = Path("data") / "statute_cache"

cache = StatuteCache(CACHE_PATH)

rag = StatuteRAG(
    embedding_model_name="sentence-transformers/all-mpnet-base-v2",
    reranking_model_name="cross-encoder/ms-marco-TinyBERT-L2-v2",
)
# rag.reset()
longest_statute_section = 0
for statute in cache:
    for section in statute.walk_sections(append_parents=True, leaf_only=True):
        t = section[1]
        if len(t) > longest_statute_section:
            print("Longer found: ", t)
            longest_statute_section = len(t)
            print()
print(f"Longest statute is {longest_statute_section} characters long.")

# for statute in cache: 
#     rag.ingest_statute(statute, verbose=True, exist_ok=True)



# res_reranked = rag.query("What does the statute say about DUIs?", top_k=10, verbose=True)
# citations = [res[1]["citation"] for res in res_reranked]
# print(citations)

# for chunk in res_reranked:
#     print()
#     print(chunk[1]["citation"])
#     print(chunk[0])
#     print()