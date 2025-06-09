#!/usr/bin/env python3
"""
metrics.py  –  Analyse logs_raw.csv produced by python_processor.py

Usage:
    python metrics.py [logs_raw.csv]

Outputs:
    • prints overall Accuracy/Precision/Recall/F1 with 95 % Wilson CIs
    • prints per-configuration confusion matrix (+ F1)
    • writes per-config summary to results_by_config.csv
"""

import sys, pandas as pd, numpy as np
from sklearn.metrics import confusion_matrix
from statsmodels.stats.proportion import proportion_confint as wilson

logfile = sys.argv[1] if len(sys.argv) > 1 else "logs_raw.csv"
df = pd.read_csv(logfile)

# ───────── helpers ───────── #
def cm_counts(sub):
    tn, fp, fn, tp = confusion_matrix(sub.truth, sub.pred).ravel()
    return tp, tn, fp, fn

def f1(tp, fp, fn):
    return 2*tp / (2*tp + fp + fn) if (2*tp + fp + fn) else 0

def ci(p, n):
    lo, hi = wilson(p*n, n, method="wilson")
    return f"[{lo:.3f},{hi:.3f}]"

# ───────── per-configuration table ───────── #
rows = []
for cfg, g in df.groupby("config"):
    tp, tn, fp, fn = cm_counts(g)
    acc = (tp+tn)/len(g)
    prec = tp/(tp+fp) if tp+fp else 0
    rec  = tp/(tp+fn) if tp+fn else 0
    rows.append([cfg, tp, tn, fp, fn, acc, prec, rec, f1(tp,fp,fn)])

pd.DataFrame(rows, columns=[
    "config","tp","tn","fp","fn","acc","prec","rec","f1"
]).to_csv("results_by_config.csv", index=False)
print("✔ results_by_config.csv written")

# ───────── overall metrics ───────── #
tp, tn, fp, fn = cm_counts(df)
N = len(df)
acc = (tp+tn)/N
prec = tp/(tp+fp) if tp+fp else 0
rec  = tp/(tp+fn) if tp+fn else 0
F1   = f1(tp,fp,fn)

print("\n=== OVERALL ===")
for name,val in [("Accuracy",acc),("Precision",prec),("Recall",rec),("F1",F1)]:
    print(f"{name:<9}: {val:.3f}  CI95 {ci(val,N)}")
print(f"TP={tp}  TN={tn}  FP={fp}  FN={fn}")
