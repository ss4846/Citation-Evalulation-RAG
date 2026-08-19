"""
Full RAGAS evaluation - all 300 answerable outputs (75 Qs × 4 conditions).
GPT-4o-mini judge. Resumable: scores saved per-output as it goes, so a
crash or rate-limit doesn't lose progress. Re-run to continue.

Output: evaluation/ragas_scores.csv
"""
import os, json, time
from dotenv import load_dotenv
load_dotenv()

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "outputs")
EVAL_DIR = os.path.join(ROOT, "evaluation")
CACHE_DIR = os.path.join(EVAL_DIR, "ragas_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CSV_PATH = os.path.join(EVAL_DIR, "ragas_scores.csv")

judge = LangchainLLMWrapper(ChatOpenAI(
    model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0.0))
embeddings = LangchainEmbeddingsWrapper(
    OpenAIEmbeddings(model="text-embedding-3-small",
                     api_key=os.getenv("OPENAI_API_KEY")))

# Gather answerable outputs
files = sorted(f for f in os.listdir(OUT_DIR) if f.endswith(".json"))
to_score = []
for f in files:
    d = json.load(open(os.path.join(OUT_DIR, f), encoding="utf-8"))
    if d.get("answerable", True):
        to_score.append((f, d))

print(f"{len(to_score)} answerable outputs to score.\n")

done = 0
for fname, d in to_score:
    cache_path = os.path.join(CACHE_DIR, fname)
    if os.path.exists(cache_path):   # resume: skip already-scored
        done += 1
        continue

    dataset = Dataset.from_dict({
        "question": [d["question"]],
        "answer": [d["answer"]],
        "contexts": [[c["text"] for c in d["retrieved"]]],
    })

    for attempt in range(1, 4):
        try:
            res = evaluate(dataset, metrics=[faithfulness, answer_relevancy],
                           llm=judge, embeddings=embeddings)
            scores = res.to_pandas().iloc[0]
            record = {
                "id": d["id"], "condition": d["condition"], "type": d["type"],
                "faithfulness": float(scores["faithfulness"]),
                "answer_relevancy": float(scores["answer_relevancy"]),
            }
            with open(cache_path, "w", encoding="utf-8") as cf:
                json.dump(record, cf)
            done += 1
            print(f"[{done}/{len(to_score)}] {d['id']} {d['condition']} "
                  f"faith={record['faithfulness']:.2f} "
                  f"rel={record['answer_relevancy']:.2f}")
            break
        except Exception as e:
            print(f"    {d['id']} {d['condition']} attempt {attempt} failed: "
                  f"{type(e).__name__}")
            if attempt < 3:
                time.sleep(10)

# Combine all cached scores into one CSV
import csv
rows = [json.load(open(os.path.join(CACHE_DIR, f), encoding="utf-8"))
        for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["id", "condition", "type",
                                      "faithfulness", "answer_relevancy"])
    w.writeheader()
    w.writerows(rows)

print(f"\nDONE. {len(rows)} scored. Saved to {CSV_PATH}")