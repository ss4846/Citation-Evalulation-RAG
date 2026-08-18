"""
test_retrieval.py - sanity check the FAISS index.
Throws a few sample legal questions at it and prints the top-5
chunks retrieved, so we can eyeball whether retrieval is sensible
BEFORE building the generation pipeline.
"""

import os
import pickle
import faiss
from sentence_transformers import SentenceTransformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(ROOT, "index", "faiss.index")
META_PATH = os.path.join(ROOT, "index", "metadata.pkl")

# Load index + metadata + model
print("Loading index and model...")
index = faiss.read_index(INDEX_PATH)
chunks = pickle.load(open(META_PATH, "rb"))
model = SentenceTransformer("all-MiniLM-L6-v2")
print(f"  {index.ntotal} vectors loaded\n")

# A few test questions spanning your question types
test_questions = [
    "What are the requirements for lawful pre-trial detention under Article 5?",
    "When can the length of detention violate the reasonable time requirement?",
    "What factors does the Court consider when assessing interference with private life under Article 8?",
]

K = 5

def retrieve(query, k=K):
    q_emb = model.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(q_emb)
    scores, idxs = index.search(q_emb, k)
    return [(chunks[i], float(s)) for i, s in zip(idxs[0], scores[0])]

for q in test_questions:
    print("=" * 70)
    print("QUESTION:", q)
    print("=" * 70)
    results = retrieve(q)
    for rank, (chunk, score) in enumerate(results, 1):
        print(f"\n[{rank}] score={score:.3f}  {chunk['case'][:45]} §{chunk['para']} ({chunk['section'][:30]})")
        print(f"    {chunk['text'][:180]}")
    print()