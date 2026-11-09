"""
DocGuard-X automated model comparison.
Run from the DocGuard-X project root:
    python compare_models.py

Uses only the published dataset's available event-level columns.
Ground-truth risk_label/risk_type are excluded from model features.
Primary features exclude action and response_status to reduce label leakage.
"""
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import IsolationForest, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.neighbors import LocalOutlierFactor
from sklearn.metrics import (
    precision_score, recall_score, f1_score, accuracy_score,
    confusion_matrix, average_precision_score, roc_auc_score
)

warnings.filterwarnings("ignore")

DATA = Path("dataset/lecheng_security_logs_2024H1_pipeline10.csv")
OUT = Path("reports/model_comparison")
OUT.mkdir(parents=True, exist_ok=True)

print("Loading dataset...")
df = pd.read_csv(DATA, parse_dates=["timestamp"])
df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
print(f"Loaded {len(df):,} rows.")

# Ground truth remains separate from feature matrix.
y = df["risk_label"].astype(int)
df["hour"] = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.dayofweek
df["month"] = df["timestamp"].dt.month

# Excluded intentionally: risk_label, risk_type, action, response_status.
numeric_features = ["volume_kb", "latency_ms", "hour", "day_of_week", "month"]
categorical_features = ["hospital_id", "is_trusted_line", "dest_platform"]
X = df[numeric_features + categorical_features].copy()
X["is_trusted_line"] = X["is_trusted_line"].astype(str)

# Chronological 80/20 holdout; no random shuffle.
split = int(len(df) * 0.80)
X_train, X_test = X.iloc[:split].copy(), X.iloc[split:].copy()
y_train, y_test = y.iloc[:split].copy(), y.iloc[split:].copy()
print(f"Chronological split: train={len(X_train):,}, test={len(X_test):,}")
print(f"Train anomaly prevalence: {y_train.mean():.3%}")
print(f"Test anomaly prevalence:  {y_test.mean():.3%}")

numeric_pipe = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])
categorical_pipe = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
])
preprocessor = ColumnTransformer([
    ("numeric", numeric_pipe, numeric_features),
    ("categorical", categorical_pipe, categorical_features)
])

print("Preparing encoded features...")
Xt_train = preprocessor.fit_transform(X_train)
Xt_test = preprocessor.transform(X_test)
print(f"Encoded feature dimensions: {Xt_train.shape[1]}")

results = []

def evaluate(name, y_true, pred, scores, note=""):
    # scores should be higher for more anomalous examples.
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    row = {
        "model": name,
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "accuracy": accuracy_score(y_true, pred),
        "false_positive_rate": fp / (fp + tn) if (fp + tn) else 0,
        "average_precision": average_precision_score(y_true, scores),
        "roc_auc": roc_auc_score(y_true, scores),
        "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
        "evaluation_note": note,
    }
    results.append(row)
    print(f"\n{name}:")
    print(f"  Precision={row['precision']:.4f}  Recall={row['recall']:.4f}  F1={row['f1']:.4f}")
    print(f"  FPR={row['false_positive_rate']:.4f}  AP={row['average_precision']:.4f}  ROC-AUC={row['roc_auc']:.4f}")
    print(f"  Confusion matrix: TN={tn:,}, FP={fp:,}, FN={fn:,}, TP={tp:,}")

# Anomaly models are trained without labels. Set anomaly threshold at 5%,
# matching the overall benchmark prevalence, and clearly note this assumption.
contamination = 0.05

print("\n[1/4] Isolation Forest (unsupervised)...")
t0 = time.time()
if_model = IsolationForest(
    n_estimators=100, contamination=contamination,
    random_state=42, n_jobs=-1
)
if_model.fit(Xt_train)
if_scores = -if_model.score_samples(Xt_test)
if_pred = (if_model.predict(Xt_test) == -1).astype(int)
evaluate("Isolation Forest", y_test, if_pred, if_scores,
         "Unsupervised; 5% contamination threshold; labels used only for evaluation.")
print(f"  Elapsed: {time.time()-t0:.1f}s")

print("\n[2/4] Random Forest (supervised)...")
t0 = time.time()
rf = RandomForestClassifier(
    n_estimators=100, max_depth=18, min_samples_leaf=3,
    class_weight="balanced_subsample", random_state=42, n_jobs=-1
)
rf.fit(Xt_train, y_train)
rf_scores = rf.predict_proba(Xt_test)[:, 1]
rf_pred = (rf_scores >= 0.5).astype(int)
evaluate("Random Forest", y_test, rf_pred, rf_scores,
         "Supervised; trained using risk_label; threshold=0.50.")
print(f"  Elapsed: {time.time()-t0:.1f}s")

print("\n[3/4] HistGradientBoosting (supervised)...")
t0 = time.time()
# HistGradientBoosting does not accept sparse matrices; the preprocessing above
# intentionally creates a dense matrix with only a few categorical levels.
hgb = HistGradientBoostingClassifier(
    max_iter=100, max_leaf_nodes=31, learning_rate=0.1,
    random_state=42
)
hgb.fit(Xt_train, y_train)
hgb_scores = hgb.predict_proba(Xt_test)[:, 1]
hgb_pred = (hgb_scores >= 0.5).astype(int)
evaluate("HistGradientBoosting", y_test, hgb_pred, hgb_scores,
         "Supervised; trained using risk_label; threshold=0.50.")
print(f"  Elapsed: {time.time()-t0:.1f}s")

print("\n[4/4] Local Outlier Factor (unsupervised; capped sample for runtime)...")
t0 = time.time()
rng = np.random.default_rng(42)
lof_train_cap = min(20000, len(Xt_train))
lof_test_cap = min(10000, len(Xt_test))
train_idx = rng.choice(len(Xt_train), size=lof_train_cap, replace=False)
test_idx = np.sort(rng.choice(len(Xt_test), size=lof_test_cap, replace=False))
lof = LocalOutlierFactor(n_neighbors=35, novelty=True, contamination=contamination, n_jobs=-1)
lof.fit(Xt_train[train_idx])
lof_scores = -lof.score_samples(Xt_test[test_idx])
lof_pred = (lof.predict(Xt_test[test_idx]) == -1).astype(int)
evaluate("Local Outlier Factor", y_test.iloc[test_idx].to_numpy(), lof_pred, lof_scores,
         f"Unsupervised; random reproducible test sample of {lof_test_cap:,}; training cap {lof_train_cap:,}; 5% contamination.")
print(f"  Elapsed: {time.time()-t0:.1f}s")

report = pd.DataFrame(results).sort_values("f1", ascending=False)
report.to_csv(OUT / "model_comparison_metrics.csv", index=False)
report.to_json(OUT / "model_comparison_metrics.json", orient="records", indent=2)

print("\n" + "="*70)
print("FINAL AUTOMATED RANKING (sorted by F1; review FPR and recall too)")
print("="*70)
display_cols = ["model", "precision", "recall", "f1", "false_positive_rate", "average_precision", "roc_auc"]
print(report[display_cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
print(f"\nSaved report files in: {OUT}")
print("NOTE: LOF is evaluated on a smaller sampled test set; do not compare its metrics as perfectly apples-to-apples.")
print("NOTE: Supervised results are a labelled-data benchmark, not unsupervised anomaly detection.")
