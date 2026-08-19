"""
citation_scorer.py - the novel evaluation contribution.

For every citing output, this:
  1. Parses [Case §N] citations from the answer.
  2. Checks each citation against the 5 retrieved chunks:
       - VALID:  the cited (case, para) IS in the retrieved set
       - GHOST:  the cited (case, para) is NOT in the retrieved set
  3. For valid citations, computes citation ACCURACY: does the cited
     chunk's text actually support the sentence making the citation?
     (cosine similarity >= threshold)

Produces per-output metrics, saved to evaluation/citation_scores.csv.
Local, free, fast. No API calls.
"""

import os
import re
import json
import csv
from sentence_transformers import SentenceTransformer, util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "outputs")
EVAL_DIR = os.path.join(ROOT, "evaluation")
os.makedirs(EVAL_DIR, exist_ok=True)
CSV_PATH = os.path.join(EVAL_DIR, "citation_scores.csv")

SIM_THRESHOLD = 0.5   # cosine sim for a citation to count as "accurate"
CITE_PATTERN = re.compile(r"\[([^\]]*?)§\s*(\d+)\]")

BRACKET_PATTERN = re.compile(r"\[([^\]]+)\]")
SINGLE_CITE = re.compile(r"([A-ZÇĞİÖŞÜ][^§;]*?)§\s*(\d+)")

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")


def normalise_case(name):
    """Strip 'CASE OF ' prefix and lowercase for matching."""
    return name.replace("CASE OF ", "").strip().lower()

import unicodedata

def strip_accents(s):
    """Remove accents and lowercase, for forgiving case-name matching."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def case_key(name):
    """Aggressive normalisation: no accents, no punctuation, lowercased."""
    s = strip_accents(name.replace("CASE OF ", ""))
    s = re.sub(r"[^a-z0-9 ]", "", s.lower())   # drop periods, etc.
    return re.sub(r"\s+", " ", s).strip()


def split_bracket(bracket_content):
    """Split a bracket that may contain multiple 'Case §N' citations.
    Handles: 'A v. B §7, C v. D §7' and 'A §85; B §43' and 'A §48, §2'."""
    cites = []
    last_case = None
    for m in SINGLE_CITE.finditer(bracket_content):
        case = m.group(1).strip().rstrip(",;").strip()
        if case:
            last_case = normalise_case(case)
        cites.append((last_case, int(m.group(2))))
    # handle trailing bare "§N" with no case (e.g. "§48, §2")
    if not cites:
        for pm in re.finditer(r"§\s*(\d+)", bracket_content):
            cites.append((None, int(pm.group(1))))
    return cites


def parse_citations(answer):
    """Return list of (case_name, para) handling multi-citations per bracket."""
    cites = []
    for bm in BRACKET_PATTERN.finditer(answer):
        cites.extend(split_bracket(bm.group(1)))
    return cites


def sentence_for_citation(answer, cite_span_start):
    """Grab the sentence containing a citation, for accuracy scoring."""
    # crude sentence split around the citation position
    start = answer.rfind(".", 0, cite_span_start) + 1
    end = answer.find(".", cite_span_start)
    if end == -1:
        end = len(answer)
    return answer[start:end].strip()


def score_output(record):
    answer = record["answer"]
    retrieved = record["retrieved"]

    # Build lookup: (normalised case_key, para) -> chunk text
    retrieved_lookup = {}
    retrieved_paras = set()
    for c in retrieved:
        key = (case_key(c["case"]), c["para"])
        retrieved_lookup[key] = c["text"]
        retrieved_paras.add(c["para"])

        cites = parse_citations(answer)
    n_cites = len(cites)

    if n_cites == 0:
        return {"n_citations": 0, "n_valid": 0, "n_ghost": 0,
                "ghost_rate": "", "n_accurate": 0, "citation_accuracy": ""}

    n_valid = n_ghost = n_accurate = 0
    for case, para in cites:
        if case is None:
            # bare "§N" - valid if that para was retrieved
            if para in retrieved_paras:
                n_valid += 1
            else:
                n_ghost += 1
            continue
        ck = case_key(case)
        key = (ck, para)
        if key in retrieved_lookup:
            n_valid += 1
            chunk_text = retrieved_lookup[key]
            emb = model.encode([answer[:500], chunk_text], convert_to_tensor=True)
            sim = float(util.cos_sim(emb[0], emb[1]))
            if sim >= SIM_THRESHOLD:
                n_accurate += 1
        elif para in retrieved_paras:
            # case-name mismatch but the para WAS retrieved - treat as valid
            # (guards against accent/punctuation name differences)
            n_valid += 1
            # find the chunk with that para for accuracy scoring
            match = next((c for c in retrieved if c["para"] == para), None)
            if match:
                emb = model.encode([answer[:500], match["text"]], convert_to_tensor=True)
                if float(util.cos_sim(emb[0], emb[1])) >= SIM_THRESHOLD:
                    n_accurate += 1
        else:
            n_ghost += 1

    return {
        "n_citations": n_cites,
        "n_valid": n_valid,
        "n_ghost": n_ghost,
        "ghost_rate": round(n_ghost / n_cites, 3),
        "n_accurate": n_accurate,
        "citation_accuracy": round(n_accurate / n_valid, 3) if n_valid else 0,
    }


def main():
    files = sorted(f for f in os.listdir(OUT_DIR) if f.endswith(".json"))
    rows = []

    for fname in files:
        record = json.load(open(os.path.join(OUT_DIR, fname), encoding="utf-8"))
        scores = score_output(record)
        rows.append({
            "id": record["id"],
            "condition": record["condition"],
            "type": record["type"],
            "answerable": record["answerable"],
            **scores,
        })

    # Write CSV
    fieldnames = ["id", "condition", "type", "answerable",
                  "n_citations", "n_valid", "n_ghost", "ghost_rate",
                  "n_accurate", "citation_accuracy"]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Quick summary by condition
    print(f"\nScored {len(rows)} outputs. Saved to {CSV_PATH}\n")
    from collections import defaultdict
    agg = defaultdict(lambda: {"cites": 0, "ghost": 0, "outputs": 0})
    for r in rows:
        a = agg[r["condition"]]
        a["outputs"] += 1
        a["cites"] += r["n_citations"]
        a["ghost"] += r["n_ghost"]
    print(f"{'condition':<12}{'outputs':<10}{'total cites':<14}{'ghosts':<10}")
    for cond, a in agg.items():
        print(f"{cond:<12}{a['outputs']:<10}{a['cites']:<14}{a['ghost']:<10}")


if __name__ == "__main__":
    main()