
"""
DocGuard-X: Model validation and threshold optimization.

Chronological split:
64% training, 16% validation, 20% final testing.

The final test set is never used to select thresholds.
"""

import time
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

from sklearn.ensemble import (
    RandomForestClassifier,
    HistGradientBoostingClassifier
)

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    confusion_matrix,
    average_precision_score,
    roc_auc_score
)

DATA = Path("dataset/lecheng_security_logs_2024H1_pipeline10.csv")
OUT = Path("reports/model_validation")
MODEL_OUT = Path("data/final_model")

OUT.mkdir(parents=True, exist_ok=True)
MODEL_OUT.mkdir(parents=True, exist_ok=True)

print("Loading dataset...")

df = pd.read_csv(DATA, parse_dates=["timestamp"])
df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)

print(f"Loaded {len(df):,} rows.")

# Prepare time features.
df["hour"] = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.dayofweek
df["month"] = df["timestamp"].dt.month

# Ground-truth labels are never included in model features.
y = df["risk_label"].astype(int)

numeric_features = [
    "volume_kb",
    "latency_ms",
    "hour",
    "day_of_week",
    "month"
]

categorical_features = [
    "hospital_id",
    "is_trusted_line",
    "dest_platform"
]

X = df[numeric_features + categorical_features].copy()
X["is_trusted_line"] = X["is_trusted_line"].astype(str)

# Chronological 64/16/20 split.
n = len(df)

train_end = int(n * 0.64)
validation_end = int(n * 0.80)

X_train = X.iloc[:train_end]
X_val = X.iloc[train_end:validation_end]
X_test = X.iloc[validation_end:]

y_train = y.iloc[:train_end]
y_val = y.iloc[train_end:validation_end]
y_test = y.iloc[validation_end:]

print("\nChronological split:")
print(f"Training:   {len(X_train):,} rows")
print(f"Validation: {len(X_val):,} rows")
print(f"Testing:    {len(X_test):,} rows")

print(f"\nTraining anomaly rate:   {y_train.mean():.3%}")
print(f"Validation anomaly rate: {y_val.mean():.3%}")
print(f"Testing anomaly rate:    {y_test.mean():.3%}")

# Preprocessing.
numeric_pipe = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_pipe = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False
    ))
])

preprocessor = ColumnTransformer([
    ("numeric", numeric_pipe, numeric_features),
    ("categorical", categorical_pipe, categorical_features)
])

print("\nPreparing features...")

Xt_train = preprocessor.fit_transform(X_train)
Xt_val = preprocessor.transform(X_val)
Xt_test = preprocessor.transform(X_test)

print(f"Encoded feature count: {Xt_train.shape[1]}")

# Find thresholds efficiently using sorted validation scores.
def threshold_analysis(y_true, scores):

    y_true = np.asarray(y_true)
    scores = np.asarray(scores)

    order = np.argsort(-scores)

    sorted_scores = scores[order]
    sorted_labels = y_true[order]

    cumulative_tp = np.cumsum(sorted_labels)
    cumulative_fp = np.cumsum(1 - sorted_labels)

    # Evaluate only at unique thresholds.
    unique_end = np.r_[
        sorted_scores[:-1] != sorted_scores[1:],
        True
    ]

    thresholds = sorted_scores[unique_end]

    tp = cumulative_tp[unique_end]
    fp = cumulative_fp[unique_end]

    total_positive = np.sum(y_true)
    total_negative = len(y_true) - total_positive

    fn = total_positive - tp
    tn = total_negative - fp

    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / max(total_positive, 1)

    fpr = fp / max(total_negative, 1)

    f1 = (
        2 * precision * recall /
        np.maximum(precision + recall, 1e-12)
    )

    table = pd.DataFrame({
        "threshold": thresholds,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fpr
    })

    # Best F1; break ties using lower false-positive rate.
    best_f1 = table.sort_values(
        ["f1", "false_positive_rate", "threshold"],
        ascending=[False, True, False]
    ).iloc[0]

    # Highest recall while maintaining FPR <= 2%.
    acceptable = table[
        table["false_positive_rate"] <= 0.02
    ]

    if len(acceptable):
        best_recall = acceptable.sort_values(
            ["recall", "precision", "false_positive_rate"],
            ascending=[False, False, True]
        ).iloc[0]
    else:
        best_recall = None

    return best_f1, best_recall


# Final evaluation function.
def evaluate(model_name, strategy, y_true, scores, threshold):

    predictions = (scores >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1]
    ).ravel()

    return {
        "model": model_name,
        "strategy": strategy,
        "threshold": float(threshold),
        "precision": precision_score(
            y_true, predictions, zero_division=0
        ),
        "recall": recall_score(
            y_true, predictions, zero_division=0
        ),
        "f1": f1_score(
            y_true, predictions, zero_division=0
        ),
        "accuracy": accuracy_score(y_true, predictions),
        "false_positive_rate": fp / max(fp + tn, 1),
        "average_precision": average_precision_score(
            y_true, scores
        ),
        "roc_auc": roc_auc_score(y_true, scores),
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp)
    }


models = {
    "Random Forest": RandomForestClassifier(
        n_estimators=100,
        max_depth=18,
        min_samples_leaf=3,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1
    ),

    "HistGradientBoosting": HistGradientBoostingClassifier(
        max_iter=100,
        max_leaf_nodes=31,
        learning_rate=0.1,
        random_state=42
    )
}

validation_choices = []
test_results = []
fitted_models = {}

for name, model in models.items():

    print("\n" + "=" * 65)
    print(f"Training {name}")
    print("=" * 65)

    start = time.time()

    model.fit(Xt_train, y_train)

    print(f"Training completed in {time.time() - start:.1f}s")

    validation_scores = model.predict_proba(Xt_val)[:, 1]
    test_scores = model.predict_proba(Xt_test)[:, 1]

    # Threshold selection uses validation labels only.
    best_f1, best_recall = threshold_analysis(
        y_val,
        validation_scores
    )

    print("\nValidation threshold choices:")

    print(
        f"Best F1 threshold: {best_f1['threshold']:.6f}"
    )
    print(
        f"Validation F1: {best_f1['f1']:.4f}"
    )
    print(
        f"Validation FPR: "
        f"{best_f1['false_positive_rate']:.4f}"
    )

    validation_choices.append({
        "model": name,
        "strategy": "best_f1",
        **best_f1.to_dict()
    })

    if best_recall is not None:

        print(
            f"Best recall threshold with FPR <= 2%: "
            f"{best_recall['threshold']:.6f}"
        )

        print(
            f"Validation recall: {best_recall['recall']:.4f}"
        )

        validation_choices.append({
            "model": name,
            "strategy": "recall_at_fpr_2_percent",
            **best_recall.to_dict()
        })

    else:
        print("No threshold met the 2% FPR requirement.")

    # Evaluate selected thresholds on the untouched test set.
    test_results.append(
        evaluate(
            name,
            "best_f1",
            y_test,
            test_scores,
            best_f1["threshold"]
        )
    )

    if best_recall is not None:

        test_results.append(
            evaluate(
                name,
                "recall_at_fpr_2_percent",
                y_test,
                test_scores,
                best_recall["threshold"]
            )
        )

    fitted_models[name] = {
        "model": model,
        "test_scores": test_scores,
        "best_f1": best_f1,
        "best_recall": best_recall
    }


# Save validation decisions.
validation_df = pd.DataFrame(validation_choices)

validation_df.to_csv(
    OUT / "validation_threshold_choices.csv",
    index=False
)

# Select the model using validation F1 only.
best_models = validation_df[
    validation_df["strategy"] == "best_f1"
].sort_values(
    ["f1", "false_positive_rate"],
    ascending=[False, True]
)

winner = best_models.iloc[0]
winner_name = winner["model"]

# Save final test results.
test_df = pd.DataFrame(test_results)

test_df.to_csv(
    OUT / "final_test_metrics.csv",
    index=False
)

test_df.to_json(
    OUT / "final_test_metrics.json",
    orient="records",
    indent=2
)

# Save the selected model and its validation-selected thresholds.
winner_info = fitted_models[winner_name]

artifact = {
    "model_name": winner_name,
    "model": winner_info["model"],
    "preprocessor": preprocessor,
    "numeric_features": numeric_features,
    "categorical_features": categorical_features,
    "best_f1_threshold": float(
        winner_info["best_f1"]["threshold"]
    ),
    "recall_threshold": (
        float(winner_info["best_recall"]["threshold"])
        if winner_info["best_recall"] is not None
        else None
    )
}

joblib.dump(
    artifact,
    MODEL_OUT / "docguard_final_model.joblib"
)

print("\n" + "=" * 65)
print("FINAL MODEL SELECTION")
print("=" * 65)

print(f"Selected model: {winner_name}")
print(f"Selection basis: validation F1")
print(f"Validation F1: {winner['f1']:.4f}")
print(
    f"Validation FPR: "
    f"{winner['false_positive_rate']:.4f}"
)

print("\nFinal untouched test results:")

print(
    test_df.to_string(
        index=False,
        float_format=lambda value: f"{value:.4f}"
    )
)

print("\nSaved files:")
print(OUT)
print(MODEL_OUT / "docguard_final_model.joblib")

print("\nIMPORTANT:")
print("Thresholds were selected using validation data only.")
print("The final test set was used only for evaluation.")
print("Supervised models use risk_label during training.")
