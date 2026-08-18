"""
index.py - embeds all paragraph chunks and builds a FAISS index.
Runs once, entirely locally. After this, retrieval is instant.

Produces:
  index/faiss.index   - the vector index
  index/metadata.pkl  - chunk metadata (case, para, section, text)
                        aligned to index positions
"""

import os
import json
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ---- Paths ----
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_PATH = os.path.join(ROOT, "data", "processed", "chunks.jsonl")
INDEX_DIR = os.path.join(ROOT, "index")
os.makedirs(INDEX_DIR, exist_ok=True)
INDEX_PATH = os.path.join(INDEX_DIR, "faiss.index")
META_PATH = os.path.join(INDEX_DIR, "metadata.pkl")

# ---- Load chunks ----
print("Loading chunks...")
chunks = [json.loads(l) for l in open(CHUNKS_PATH, encoding="utf-8")]
texts = [c["text"] for c in chunks]
print(f"  {len(chunks)} chunks loaded")

# ---- Load embedding model ----
print("Loading embedding model (all-MiniLM-L6-v2)...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# ---- Embed all chunks ----
print(f"Embedding {len(texts)} chunks (this takes a few minutes)...")
embeddings = model.encode(
    texts,
    show_progress_bar=True,
    batch_size=64,
    convert_to_numpy=True,
)
embeddings = embeddings.astype("float32")
print(f"  embeddings shape: {embeddings.shape}")

# ---- Normalise for cosine similarity ----
# FAISS IndexFlatIP + normalised vectors = cosine similarity search
faiss.normalize_L2(embeddings)

# ---- Build FAISS index ----
dim = embeddings.shape[1]
index = faiss.IndexFlatIP(dim)   # inner product on normalised vectors = cosine
index.add(embeddings)
print(f"  index built with {index.ntotal} vectors, dim={dim}")

# ---- Save index + metadata ----
faiss.write_index(index, INDEX_PATH)
with open(META_PATH, "wb") as f:
    pickle.dump(chunks, f)

print()
print("=" * 55)
print("DONE.")
print(f"  Index:    {INDEX_PATH}")
print(f"  Metadata: {META_PATH}")
print("=" * 55)