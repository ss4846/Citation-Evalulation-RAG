"""Assembles the 75 approved answerable questions from candidates.jsonl
into final_answerable.jsonl. Applies the two hand-edits to Q050 and Q067.
Original candidates.jsonl is left untouched."""
import os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(ROOT, "data", "questions", "candidates.jsonl")
OUT = os.path.join(ROOT, "data", "questions", "final_answerable.jsonl")

KEEP = {
    "factual": "Q002 Q003 Q005 Q007 Q008 Q009 Q010 Q011 Q013 Q014 Q016 Q017 Q018 Q020 Q021 Q023 Q024 Q025 Q027 Q029 Q031 Q032 Q033 Q034 Q035".split(),
    "principle": "Q036 Q038 Q039 Q041 Q042 Q043 Q044 Q045 Q046 Q048 Q050 Q052 Q056 Q057 Q059 Q060 Q061 Q062 Q063 Q064 Q066 Q067 Q068 Q069 Q070".split(),
    "cross_case": "Q071 Q072 Q073 Q074 Q075 Q077 Q078 Q079 Q080 Q081 Q082 Q083 Q084 Q085 Q086 Q087 Q088 Q089 Q090 Q091 Q092 Q093 Q096 Q099 Q100".split(),
}

# Hand-edits: case names stripped so retrieval isn't trivially easy
EDITS = {
    "Q050": "What legal principle governs the sufficiency of an investigation into credible allegations of ill-treatment in police custody under Article 3 of the Convention?",
    "Q067": "Under what circumstances may a government be held liable for the excessive length of criminal proceedings under the Convention?",
}

all_keep = set(sum(KEEP.values(), []))
cands = {json.loads(l)["id"]: json.loads(l) for l in open(CAND, encoding="utf-8")}

final = []
missing = []
for qid in sorted(all_keep):
    if qid not in cands:
        missing.append(qid); continue
    q = cands[qid]
    if qid in EDITS:
        q["question"] = EDITS[qid]
        q["edited"] = True
    q["answerable"] = True
    final.append(q)

if missing:
    print("WARNING - these IDs weren't found:", missing)

with open(OUT, "w", encoding="utf-8") as f:
    for q in final:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")

from collections import Counter
by_type = Counter(q["type"] for q in final)
print(f"Wrote {len(final)} answerable questions to final_answerable.jsonl")
print("By type:", dict(by_type))