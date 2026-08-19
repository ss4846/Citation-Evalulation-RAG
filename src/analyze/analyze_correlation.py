"""
RQ4: Does citation accuracy correlate with answer faithfulness?
Merges citation_scores.csv and ragas_scores.csv on (id, condition).
Correlates per-output citation_accuracy vs faithfulness. Scatter plot.
Only citing conditions with valid citations are included.
"""
import os
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL = os.path.join(ROOT, "evaluation")
FIG_DIR = os.path.join(ROOT, "analysis")
os.makedirs(FIG_DIR, exist_ok=True)

cit = pd.read_csv(os.path.join(EVAL, "citation_scores.csv"))
rag = pd.read_csv(os.path.join(EVAL, "ragas_scores.csv"))

# Merge on id + condition
merged = pd.merge(cit, rag, on=["id", "condition"], suffixes=("_cit", "_rag"))

# Keep only outputs that produced valid citations AND have a faithfulness score
merged = merged[(merged["n_valid"] > 0) & merged["faithfulness"].notna()]
# citation_accuracy is blank for non-citing outputs; coerce to numeric
merged["citation_accuracy"] = pd.to_numeric(merged["citation_accuracy"],
                                            errors="coerce")
merged = merged.dropna(subset=["citation_accuracy"])

print(f"Correlating on {len(merged)} outputs (citing, with both scores)\n")

# --- Overall correlation ---
x = merged["citation_accuracy"]
y = merged["faithfulness"]
pear_r, pear_p = stats.pearsonr(x, y)
spear_r, spear_p = stats.spearmanr(x, y)

print("CITATION ACCURACY vs FAITHFULNESS")
print(f"  Pearson  r = {pear_r:.3f}, p = {pear_p:.4f}")
print(f"  Spearman r = {spear_r:.3f}, p = {spear_p:.4f}")
print("  -> " + ("significant correlation" if pear_p < 0.05
                 else "no significant correlation"))

# --- Per-condition correlation ---
print("\nBy condition:")
for cond in ["inline", "footnote", "cot"]:
    sub = merged[merged["condition"] == cond]
    if len(sub) > 3:
        r, p = stats.pearsonr(sub["citation_accuracy"], sub["faithfulness"])
        print(f"  {cond:<10} r={r:.3f}, p={p:.4f}, n={len(sub)}")

# --- Scatter plot ---
colors = {"inline": "#4C72B0", "footnote": "#55A868", "cot": "#C44E52"}
fig, ax = plt.subplots(figsize=(7, 5.5))
for cond in ["inline", "footnote", "cot"]:
    sub = merged[merged["condition"] == cond]
    ax.scatter(sub["citation_accuracy"], sub["faithfulness"],
               label=cond, alpha=0.6, color=colors[cond], s=40)
# overall trend line
if len(merged) > 2:
    m, b = pd.np.polyfit(x, y, 1) if hasattr(pd, "np") else \
        __import__("numpy").polyfit(x, y, 1)
    xs = sorted(x)
    ax.plot(xs, [m*xi + b for xi in xs], "k--", alpha=0.5,
            label=f"trend (r={pear_r:.2f})")
ax.set_xlabel("Citation Accuracy")
ax.set_ylabel("RAGAS Faithfulness")
ax.set_title("Citation Accuracy vs Faithfulness (RQ4)")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "rq4_correlation.png"), dpi=200)
print(f"\nSaved: rq4_correlation.png")