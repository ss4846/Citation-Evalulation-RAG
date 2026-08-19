"""
Re-scores citation accuracy at multiple similarity thresholds to show
whether conclusions are stable regardless of the (somewhat arbitrary)
0.5 cutoff. Ghost detection is threshold-independent, so only accuracy
is swept here. Local, instant, no API.
"""
import os, re, json, unicodedata
from collections import defaultdict
from sentence_transformers import SentenceTransformer, util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "outputs")

THRESHOLDS = [0.4, 0.5, 0.6, 0.7]
BR = re.compile(r"\[([^\]]+)\]")
SC = re.compile(r"([A-Za-zÀ-ÿ][^§;]*?)§\s*(\d+)")

print("Loading model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

def ck(s):
    s = unicodedata.normalize("NFKD", s.replace("CASE OF ", ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", s.lower())).strip()

def parse(answer):
    cites = []
    for bm in BR.finditer(answer):
        last = None
        for m in SC.finditer(bm.group(1)):
            case = m.group(1).strip().rstrip(",;").strip()
            if case: last = ck(case)
            cites.append((last, int(m.group(2))))
    return cites

# similarity is computed ONCE per valid citation; thresholds just re-bin it
# accumulate: condition -> list of similarity scores for valid citations
sims_by_cond = defaultdict(list)

files = [f for f in os.listdir(OUT_DIR) if f.endswith(".json")]
for fname in files:
    d = json.load(open(os.path.join(OUT_DIR, fname), encoding="utf-8"))
    cond = d["condition"]
    answer = d["answer"]
    retr_lookup = {(ck(c["case"]), c["para"]): c["text"] for c in d["retrieved"]}
    retr_paras = {c["para"]: c["text"] for c in d["retrieved"]}
    for case, para in parse(answer):
        chunk = None
        if (case, para) in retr_lookup:
            chunk = retr_lookup[(case, para)]
        elif para in retr_paras:
            chunk = retr_paras[para]
        if chunk is None:
            continue  # ghost - not counted in accuracy
        emb = model.encode([answer[:500], chunk], convert_to_tensor=True)
        sims_by_cond[cond].append(float(util.cos_sim(emb[0], emb[1])))

print(f"\n{'condition':<12}" + "".join(f"acc@{t:<7}" for t in THRESHOLDS) + "n_valid")
print("-" * 60)
for cond in ["inline", "footnote", "cot"]:
    sims = sims_by_cond.get(cond, [])
    if not sims:
        continue
    row = f"{cond:<12}"
    for t in THRESHOLDS:
        acc = sum(1 for s in sims if s >= t) / len(sims)
        row += f"{acc:<10.3f}"
    row += str(len(sims))
    print(row)
print("\nIf the RANKING of conditions is the same across columns,")
print("your accuracy conclusions are threshold-robust.")