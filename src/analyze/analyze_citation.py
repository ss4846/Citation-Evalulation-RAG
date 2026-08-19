"""
RQ2: How accurate are the citations, and how often are they ghosts?
Reads citation_scores.csv. Reports citation accuracy + ghost rate per
citing condition (baseline excluded - it doesn't cite). Two bar charts.
"""
import os
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL = os.path.join(ROOT, "evaluation")
FIG_DIR = os.path.join(ROOT, "analysis")
os.makedirs(FIG_DIR, exist_ok=True)

df = pd.read_csv(os.path.join(EVAL, "citation_scores.csv"))

# Only conditions that actually cite
CITING = ["inline", "footnote", "cot"]
df = df[df["condition"].isin(CITING)]

print("CITATION METRICS BY CONDITION")
print(f"{'condition':<12}{'tot_cites':<11}{'ghosts':<9}{'ghost_rate':<12}"
      f"{'mean_acc':<10}")
print("-" * 54)

summary = {}
for cond in CITING:
    sub = df[df["condition"] == cond]
    total_cites = sub["n_citations"].sum()
    total_ghost = sub["n_ghost"].sum()
    ghost_rate = total_ghost / total_cites if total_cites else 0
    # mean citation accuracy across outputs that produced valid citations
    acc_vals = sub[sub["n_valid"] > 0]["citation_accuracy"]
    mean_acc = acc_vals.mean() if len(acc_vals) else 0
    summary[cond] = {"total_cites": total_cites, "ghosts": total_ghost,
                     "ghost_rate": ghost_rate, "mean_acc": mean_acc}
    print(f"{cond:<12}{total_cites:<11}{total_ghost:<9}"
          f"{ghost_rate:<12.4f}{mean_acc:<10.3f}")

# --- Chart 1: citation accuracy ---
fig, ax = plt.subplots(figsize=(6.5, 5))
accs = [summary[c]["mean_acc"] for c in CITING]
bars = ax.bar(CITING, accs, color=["#4C72B0", "#55A868", "#C44E52"])
ax.set_ylabel("Mean Citation Accuracy")
ax.set_title("Citation Accuracy by Condition (RQ2)")
ax.set_ylim(0, 1.0)
for b, v in zip(bars, accs):
    ax.text(b.get_x()+b.get_width()/2, v+0.02, f"{v:.3f}", ha="center")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "rq2_citation_accuracy.png"), dpi=200)
print(f"\nSaved: rq2_citation_accuracy.png")

# --- Chart 2: ghost rate ---
fig, ax = plt.subplots(figsize=(6.5, 6))
ghosts = [summary[c]["ghost_rate"]*100 for c in CITING]
bars = ax.bar(CITING, ghosts, color=["#4C72B0", "#55A868", "#C44E52"])
ax.set_ylabel("Ghost Citation Rate (%)")
ax.set_title("Ghost Citation Rate by Condition (RQ2)")
for b, v in zip(bars, ghosts):
    ax.text(b.get_x()+b.get_width()/2, v+0.01, f"{v:.2f}%", ha="center")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "rq2_ghost_rate.png"), dpi=200)
print(f"Saved: rq2_ghost_rate.png")