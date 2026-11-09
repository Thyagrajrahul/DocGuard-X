
import pandas as pd
import pickle

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
FEATURES_FILE = "data/revised_ml_features.csv"
LABELS_FILE = "data/revised_ml_labels.csv"
MODEL_FILE = "data/revised_isolation_forest.pkl"

# Load features and labels
X = pd.read_csv(FEATURES_FILE)
labels = pd.read_csv(LABELS_FILE)

y = labels["is_anomaly"]

# Confirm that both files contain matching records
if len(X) != len(y):
    raise ValueError("Feature and label files have different row counts.")

if X.isnull().sum().sum() > 0:
    raise ValueError("Feature file contains missing values.")

# Chronological 80/20 split
split_index = int(len(X) * 0.80)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

# Train only on normal training activities
X_train_normal = X_train[y_train == 0]

if len(X_train_normal) == 0:
    raise ValueError("No normal records available for training.")

print("CHRONOLOGICAL DATA SPLIT")
print("Training records:", len(X_train))
print("Testing records:", len(X_test))
print("Normal training records:", len(X_train_normal))
print("Anomaly training records:", int(y_train.sum()))
print("Normal testing records:", int((y_test == 0).sum()))
print("Anomaly testing records:", int(y_test.sum()))

# Create Isolation Forest model
model = IsolationForest(
    n_estimators=100,
    contamination="auto",
    random_state=42
)

# Train model using normal activities only
model.fit(X_train_normal)

# Predict testing records
predictions = model.predict(X_test)

# Convert predictions:
# Isolation Forest: 1 = normal, -1 = anomaly
# Our labels: 0 = normal, 1 = anomaly
y_pred = (predictions == -1).astype(int)

# Evaluate model
print("\nMODEL EVALUATION")
print("Accuracy:", round(accuracy_score(y_test, y_pred), 4))
print("Precision:", round(precision_score(y_test, y_pred, zero_division=0), 4))
print("Recall:", round(recall_score(y_test, y_pred, zero_division=0), 4))
print("F1 Score:", round(f1_score(y_test, y_pred, zero_division=0), 4))

print("\nCONFUSION MATRIX")
print(confusion_matrix(y_test, y_pred, labels=[0, 1]))

print("\nCLASSIFICATION REPORT")
print(classification_report(
    y_test,
    y_pred,
    labels=[0, 1],
    target_names=["Normal", "Anomaly"],
    zero_division=0
))

print("\nPREDICTION COUNTS")
print("Predicted normal:", int((y_pred == 0).sum()))
print("Predicted anomalies:", int((y_pred == 1).sum()))

# Save model and feature names
with open(MODEL_FILE, "wb") as file:
    pickle.dump({
        "model": model,
        "feature_columns": X.columns.tolist()
    }, file)

print("\nModel saved to:", MODEL_FILE)
