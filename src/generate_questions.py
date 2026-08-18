"""
generate_questions.py - drafts candidate questions grounded in real
corpus paragraphs, for the three ANSWERABLE question types.
(The 25 unanswerable questions are hand-written separately.)

For each question it records the source chunk (case + para) as the
'gold' answer location, so you have ground truth to verify against.

Output: data/questions/candidates.jsonl
"""

import os
import json
import time
import random
import pickle
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_PATH = os.path.join(ROOT, "index", "metadata.pkl")
QDIR = os.path.join(ROOT, "data", "questions")
os.makedirs(QDIR, exist_ok=True)
OUT_PATH = os.path.join(QDIR, "candidates.jsonl")

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
MODEL = "mistral-small-latest"

# How many candidates to draft per type (draft extra - you'll cut some)
COUNTS = {"factual": 35, "principle": 35, "cross_case": 20}

# Prompt templates per question type
PROMPTS = {
    "factual": (
        "You are helping build a legal question-answering test set from "
        "European Court of Human Rights judgments.\n\n"
        "Below is a paragraph from the case '{case}' (paragraph {para}).\n\n"
        "PARAGRAPH:\n{text}\n\n"
        "Write ONE specific, factual question that this paragraph directly "
        "answers. The question must have a clear, verifiable answer found in "
        "this exact paragraph. Do not mention the paragraph number in the "
        "question. Return ONLY the question, nothing else."
    ),
    "principle": (
        "You are helping build a legal question-answering test set from "
        "European Court of Human Rights judgments.\n\n"
        "Below is a paragraph from '{case}' (paragraph {para}) that states a "
        "legal principle or standard.\n\n"
        "PARAGRAPH:\n{text}\n\n"
        "Write ONE question asking about the legal principle or standard "
        "described here. The answer should require citing this paragraph. "
        "Do not mention the paragraph number. Return ONLY the question."
    ),
    "cross_case": (
        "You are helping build a legal question-answering test set from "
        "European Court of Human Rights judgments.\n\n"
        "Below is a paragraph from '{case}' (paragraph {para}) about a legal "
        "topic under the European Convention on Human Rights.\n\n"
        "PARAGRAPH:\n{text}\n\n"
        "Write ONE broad question about this legal topic that could plausibly "
        "be answered by drawing on MULTIPLE cases addressing the same issue "
        "(not just this one). Do not mention the paragraph number or the case "
        "name. Return ONLY the question."
    ),
}


def load_chunks():
    return pickle.load(open(META_PATH, "rb"))


def good_candidate_chunk(c, qtype):
    """Pick chunks likely to yield good questions of each type."""
    text_len = len(c["text"])
    section = c["section"].upper()
    if text_len < 150:            # too short to ground a question
        return False
    if qtype == "principle":
        # principles live in THE LAW / merits sections
        return "LAW" in section or "VIOLATION" in section or "MERITS" in section
    if qtype == "factual":
        # facts live in circumstances / facts sections
        return "FACT" in section or "CIRCUMSTANCE" in section or "PROCEDURE" in section
    if qtype == "cross_case":
        return "LAW" in section or "VIOLATION" in section
    return True


def draft_question(chunk, qtype, retries=3):
    prompt = PROMPTS[qtype].format(
        case=chunk["case"], para=chunk["para"], text=chunk["text"][:1500]
    )
    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.complete(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=120,
            )
            return resp.choices[0].message.content.strip().strip('"')
        except Exception as e:
            print(f"      API attempt {attempt} failed: {type(e).__name__}")
            if attempt < retries:
                time.sleep(5)
    return None


def main():
    chunks = load_chunks()
    random.seed(42)  # reproducible sampling

    candidates = []
    qid = 1

    for qtype, n in COUNTS.items():
        print(f"\nDrafting {n} '{qtype}' questions...")
        eligible = [c for c in chunks if good_candidate_chunk(c, qtype)]
        random.shuffle(eligible)
        picked = eligible[:n]

        for chunk in picked:
            q = draft_question(chunk, qtype)
            if q is None:
                continue
            candidates.append({
                "id": f"Q{qid:03d}",
                "type": qtype,
                "question": q,
                "gold_case": chunk["case"],
                "gold_para": chunk["para"],
                "gold_section": chunk["section"],
                "gold_text": chunk["text"][:500],
            })
            print(f"  [{qid:03d}] {q[:70]}")
            qid += 1
            time.sleep(1.5)  # polite rate limiting

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print("\n" + "=" * 60)
    print(f"Drafted {len(candidates)} candidate questions.")
    print(f"Saved to: {OUT_PATH}")
    print("Now review them by hand - keep the good ones, cut weak ones.")
    print("=" * 60)


if __name__ == "__main__":
    main()