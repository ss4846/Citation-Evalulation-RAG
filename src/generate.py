"""
generate.py - the core experiment.

For each of the 100 questions, retrieves top-5 chunks (identical across
conditions), then generates an answer under all 4 prompting conditions
using Mistral. Saves all 400 outputs.

Fully resumable: each output is saved as its own file the moment it's
produced. Re-running skips already-completed (question, condition) pairs.
"""

import os
import json
import time
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

# ---- Paths ----
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(ROOT, "index", "faiss.index")
META_PATH = os.path.join(ROOT, "index", "metadata.pkl")
QUESTIONS_PATH = os.path.join(ROOT, "data", "questions", "final_questions.jsonl")
PROMPTS_DIR = os.path.join(ROOT, "prompts")
OUT_DIR = os.path.join(ROOT, "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

# ---- Config ----
MODEL = "mistral-small-latest"
K = 5
CONDITIONS = ["baseline", "inline", "footnote", "cot"]

# ---- Load everything ----
print("Loading index, model, questions, prompts...")
index = faiss.read_index(INDEX_PATH)
chunks = pickle.load(open(META_PATH, "rb"))
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

questions = [json.loads(l) for l in open(QUESTIONS_PATH, encoding="utf-8")]
prompts = {c: open(os.path.join(PROMPTS_DIR, f"{c}.txt"), encoding="utf-8").read()
           for c in CONDITIONS}
print(f"  {len(questions)} questions, {len(CONDITIONS)} conditions "
      f"= {len(questions)*len(CONDITIONS)} total generations\n")


def retrieve(query, k=K):
    """Return top-k chunks for a query."""
    q_emb = embed_model.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(q_emb)
    scores, idxs = index.search(q_emb, k)
    return [chunks[i] for i in idxs[0]]


def format_context(retrieved):
    """Format retrieved chunks with their [Case §N] labels."""
    lines = []
    for c in retrieved:
        short_case = c["case"].replace("CASE OF ", "").strip()
        lines.append(f"[{short_case} §{c['para']}]\n{c['text']}")
    return "\n\n".join(lines)


def call_mistral(prompt, retries=4):
    """Call Mistral with retry + backoff for rate limits."""
    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.complete(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,   # deterministic - important for reproducibility
                max_tokens=800,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            wait = 5 * attempt
            print(f"      API attempt {attempt} failed ({type(e).__name__}); "
                  f"waiting {wait}s")
            if attempt < retries:
                time.sleep(wait)
    return None


def output_path(qid, condition):
    return os.path.join(OUT_DIR, f"{qid}_{condition}.json")


def main():
    total = len(questions) * len(CONDITIONS)
    done = 0
    skipped = 0

    for q in questions:
        qid = q["id"]
        # Retrieve ONCE per question - same context for all 4 conditions
        retrieved = retrieve(q["question"])
        context = format_context(retrieved)
        # Record which chunks were retrieved (for evaluation later)
        retrieved_meta = [{"case": c["case"], "para": c["para"],
                           "section": c["section"], "text": c["text"]}
                          for c in retrieved]

        for condition in CONDITIONS:
            path = output_path(qid, condition)
            # Resume: skip if already done
            if os.path.exists(path):
                skipped += 1
                done += 1
                continue

            prompt = prompts[condition].format(context=context,
                                               question=q["question"])
            answer = call_mistral(prompt)
            if answer is None:
                print(f"  {qid} [{condition}] FAILED - will retry on next run")
                continue

            record = {
                "id": qid,
                "condition": condition,
                "type": q["type"],
                "answerable": q.get("answerable", True),
                "question": q["question"],
                "gold_case": q.get("gold_case"),
                "gold_para": q.get("gold_para"),
                "retrieved": retrieved_meta,
                "answer": answer,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            done += 1
            print(f"  [{done}/{total}] {qid} [{condition}] done "
                  f"({len(answer)} chars)")
            time.sleep(1.5)  # polite rate limiting

    print("\n" + "=" * 55)
    print(f"DONE. {done}/{total} generations complete "
          f"({skipped} skipped as already-done).")
    print(f"Outputs in: {OUT_DIR}")
    print("=" * 55)


if __name__ == "__main__":
    main()