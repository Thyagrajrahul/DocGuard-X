
import os
import joblib
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

# File paths
FEATURES_FILE = "data/experimental_ml_features.csv"
LABELS_FILE = "data/experimental_ml_labels.csv"
MODEL_FILE = "data/experimental_isolation_forest.pkl"

# Load features and labels
print("Loading experimental features and labels...")

X = pd.read_csv(FEATURES_FILE)
labels = pd.read_csv(LABELS_FILE)

# Verify that both files match
if len(X) != len(labels):
    raise ValueError("Feature and label row counts do not match.")

if X.empty:
    raise ValueError("The dataset is empty.")

# Ground-truth labels: 0 = normal, 1 = anomaly
y = labels["is_anomaly"].astype(int)

# Chronological 80/20 split
split_index = int(len(X) * 0.80)

X_train = X.iloc[:split_index].copy()
X_test = X.iloc[split_index:].copy()

y_train = y.iloc[:split_index].copy()
y_test = y.iloc[split_index:].copy()

print("\nDATASET SPLIT")
print("------------------------------")
print("Total records:", len(X))
print("Training records:", len(X_train))
print("Testing records:", len(X_test))
print("Normal training records:", (y_train == 0).sum())
print("Anomaly training records:", (y_train == 1).sum())
print("Normal testing records:", (y_test == 0).sum())
print("Anomaly testing records:", (y_test == 1).sum())

# Train only on normal training records
X_train_normal = X_train[y_train == 0]

if len(X_train_normal) == 0:
    raise ValueError("No normal records available for training.")

print("\nTraining Isolation Forest...")

model = IsolationForest(
    n_estimators=100,
    contamination="auto",
    random_state=42
)

model.fit(X_train_normal)

# Predict on unseen test records
# Isolation Forest: 1 = normal, -1 = anomaly
raw_predictions = model.predict(X_test)

# Convert predictions to our label format:
# 0 = normal, 1 = anomaly
y_pred = (raw_predictions == -1).astype(int)

# Calculate evaluation metrics
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)

cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

tn, fp, fn, tp = cm.ravel()

false_positive_rate = (
    fp / (fp + tn) if (fp + tn) > 0 else 0
)

# Display results
print("\nEXPERIMENTAL MODEL RESULTS")
print("==============================")
print(f"Accuracy:            {accuracy:.4f}")
print(f"Precision:           {precision:.4f}")
print(f"Recall:              {recall:.4f}")
print(f"F1-score:            {f1:.4f}")
print(f"False-positive rate: {false_positive_rate:.4f}")

print("\nCONFUSION MATRIX")
print("------------------------------")
print("Rows = Actual, Columns = Predicted")
print("Order: Normal (0), Anomaly (1)")
print(cm)

print("\nCONFUSION MATRIX DETAILS")
print("------------------------------")
print("True Negatives:", tn)
print("False Positives:", fp)
print("False Negatives:", fn)
print("True Positives:", tp)

print("\nCLASSIFICATION REPORT")
print("------------------------------")
print(
    classification_report(
        y_test,
        y_pred,
        labels=[0, 1],
        target_names=["Normal", "Anomaly"],
        zero_division=0
    )
)

# Save model and feature information
os.makedirs("data", exist_ok=True)

joblib.dump(
    {
        "model": model,
        "feature_names": X.columns.tolist()
    },
    MODEL_FILE
)

print("\nModel saved successfully:")
print(MODEL_FILE)
