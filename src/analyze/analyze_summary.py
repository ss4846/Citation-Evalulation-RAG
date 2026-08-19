"""
RQ3: Which citation strategy is best overall?
Pulls together every metric into one comparison table + one grouped chart.
Reads all three evaluation CSVs.
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL = os.path.join(ROOT, "evaluation")
FIG_DIR = os.path.join(ROOT, "analysis")
os.makedirs(FIG_DIR, exist_ok=True)

cit = pd.read_csv(os.path.join(EVAL, "citation_scores.csv"))
rag = pd.read_csv(os.path.join(EVAL, "ragas_scores.csv"))

CONDITIONS = ["baseline", "inline", "footnote", "cot"]

# Abstention rates (hand-verified footnote=0.92; others from detector).
# Adjust these to your final verified numbers.
ABSTENTION = {"baseline": 1.00, "inline": 0.96, "footnote": 0.92, "cot": 0.88}

rows = []
for cond in CONDITIONS:
    r = rag[rag["condition"] == cond]
    c = cit[cit["condition"] == cond]
    total_cites = c["n_citations"].sum()
    total_ghost = c["n_ghost"].sum()
    acc_vals = c[c["n_valid"] > 0]["citation_accuracy"]
    rows.append({
        "condition": cond,
        "faithfulness": round(r["faithfulness"].mean(), 3),
        "answer_relevancy": round(r["answer_relevancy"].mean(), 3),
        "total_citations": int(total_cites),
        "citation_accuracy": round(acc_vals.mean(), 3) if len(acc_vals) else 0.0,
        "ghost_rate_%": round(100*total_ghost/total_cites, 3) if total_cites else 0.0,
        "abstention": ABSTENTION[cond],
    })

table = pd.DataFrame(rows).set_index("condition")
print("COMBINED COMPARISON TABLE (RQ3)\n")
print(table.to_string())

# Save table as CSV for the dissertation
table.to_csv(os.path.join(EVAL, "rq3_summary_table.csv"))
print(f"\nTable saved: evaluation/rq3_summary_table.csv")

# --- Grouped bar chart: faithfulness, citation accuracy, abstention ---
metrics = ["faithfulness", "citation_accuracy", "abstention"]
x = np.arange(len(CONDITIONS))
width = 0.25
fig, ax = plt.subplots(figsize=(9, 5.5))
for i, metric in enumerate(metrics):
    vals = [table.loc[c, metric] for c in CONDITIONS]
    ax.bar(x + i*width, vals, width, label=metric.replace("_", " "))
ax.set_xticks(x + width)
ax.set_xticklabels(CONDITIONS)
ax.set_ylabel("Score")
ax.set_title("Comparison Across Conditions (RQ3)")
ax.set_ylim(0, 1.05)
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "rq3_comparison.png"), dpi=200)
print("Chart saved: rq3_comparison.png")