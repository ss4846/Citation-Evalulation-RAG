"""
RQ1: Does citation-forcing reduce hallucination?
Reads ragas_scores.csv, compares faithfulness across conditions,
runs Kruskal-Wallis + pairwise Mann-Whitney vs baseline, makes a bar chart.
"""
import os
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL = os.path.join(ROOT, "evaluation")
FIG_DIR = os.path.join(ROOT, "analysis")
os.makedirs(FIG_DIR, exist_ok=True)

df = pd.read_csv(os.path.join(EVAL, "ragas_scores.csv"))
# Drop any NaN faithfulness rows (RAGAS occasionally can't score short answers)
before = len(df)
df = df.dropna(subset=["faithfulness"])
print(f"Loaded {before} rows, {len(df)} after dropping NaN faithfulness\n")

CONDITIONS = ["baseline", "inline", "footnote", "cot"]

# --- Summary stats per condition ---
print("FAITHFULNESS BY CONDITION")
print(f"{'condition':<12}{'mean':<8}{'median':<8}{'std':<8}{'n':<5}")
print("-" * 41)
summary = {}
for cond in CONDITIONS:
    vals = df[df["condition"] == cond]["faithfulness"]
    summary[cond] = vals
    print(f"{cond:<12}{vals.mean():<8.3f}{vals.median():<8.3f}"
          f"{vals.std():<8.3f}{len(vals):<5}")

# --- Build a paired table: one row per question, columns = conditions ---
pivot = df.pivot_table(index="id", columns="condition",
                       values="faithfulness")
# keep only questions that have all four conditions scored (drops the 1 NaN)
pivot = pivot.dropna()
print(f"\nPaired analysis on {len(pivot)} questions with all 4 conditions\n")

#  Omnibus: Friedman test (paired equivalent of Kruskal-Wallis) 
fr_stat, fr_p = stats.friedmanchisquare(
    pivot["baseline"], pivot["inline"], pivot["footnote"], pivot["cot"])
print(f"Friedman test (paired, all 4): chi2={fr_stat:.3f}, p={fr_p:.4f}")
print("  -> " + ("conditions differ significantly" if fr_p < 0.05
                 else "no significant overall difference"))

#  Pairwise: Wilcoxon signed-rank, each condition vs baseline 
print("\nPairwise vs baseline (Wilcoxon signed-rank, paired):")
for cond in ["inline", "footnote", "cot"]:
    w, pw = stats.wilcoxon(pivot[cond], pivot["baseline"])
    direction = ("higher" if pivot[cond].mean() > pivot["baseline"].mean()
                 else "lower")
    print(f"  {cond:<10} vs baseline: W={w:.1f}, p={pw:.4f}  "
          f"({cond} faithfulness is {direction})")

# --- Bar chart with error bars ---
means = [summary[c].mean() for c in CONDITIONS]
sems = [summary[c].sem() for c in CONDITIONS]

fig, ax = plt.subplots(figsize=(7, 5))
bars = ax.bar(CONDITIONS, means, yerr=sems, capsize=5,
              color=["#888888", "#4C72B0", "#55A868", "#C44E52"])
ax.set_ylabel("Mean RAGAS Faithfulness")
ax.set_xlabel("Condition")
ax.set_title("Faithfulness by Citation Condition (RQ1)")
ax.set_ylim(0, 1.0)
for bar, m in zip(bars, means):
    ax.text(bar.get_x() + bar.get_width()/2, m + 0.02, f"{m:.3f}",
            ha="center", va="bottom", fontsize=10)
plt.tight_layout()
out = os.path.join(FIG_DIR, "rq1_faithfulness.png")
plt.savefig(out, dpi=200)
print(f"\nChart saved: {out}")