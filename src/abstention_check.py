"""
Checks how often each condition correctly ABSTAINS on the 25
unanswerable questions vs forcing an (ungrounded) answer.
A correct abstention contains phrases like 'cannot', 'does not contain',
'no information', etc. Local, fast.
"""
import os, json, re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "outputs")

# Phrases that signal the model recognised it couldn't answer
ABSTAIN_SIGNALS = [
    "does not contain", "do not contain", "cannot answer", "can't answer",
    "not contain enough", "no information", "does not provide", "do not provide",
    "not possible to answer", "unable to answer", "context does not",
    "not mentioned", "not addressed", "not discussed", "insufficient",
    "not enough information", "does not mention", "no relevant",
    "not explicitly", "does not explicitly", "do not explicitly",
    "does not directly address", "does not address", "do not address",
    "does not set out", "does not specify", "does not detail",
    "not provided", "no specific", "not specify", "does not appear",
]

def abstained(answer):
    a = answer.lower()
    return any(sig in a for sig in ABSTAIN_SIGNALS)

results = defaultdict(lambda: {"total": 0, "abstained": 0})

for fname in os.listdir(OUT_DIR):
    if not fname.endswith(".json"):
        continue
    d = json.load(open(os.path.join(OUT_DIR, fname), encoding="utf-8"))
    if d.get("answerable", True):
        continue  # only unanswerable questions
    cond = d["condition"]
    results[cond]["total"] += 1
    if abstained(d["answer"]):
        results[cond]["abstained"] += 1

print(f"\nABSTENTION ON UNANSWERABLE QUESTIONS (should be high = good)\n")
print(f"{'condition':<12}{'abstained':<12}{'total':<8}{'rate':<8}")
print("-" * 40)
for cond in ["baseline", "inline", "footnote", "cot"]:
    r = results[cond]
    if r["total"]:
        rate = r["abstained"] / r["total"]
        print(f"{cond:<12}{r['abstained']:<12}{r['total']:<8}{rate:<8.2f}")