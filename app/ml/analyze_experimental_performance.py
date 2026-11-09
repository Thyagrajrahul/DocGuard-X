
import joblib
import pandas as pd

from sklearn.metrics import confusion_matrix

# File paths
FEATURES_FILE = "data/experimental_ml_features.csv"
LABELS_FILE = "data/experimental_ml_labels.csv"
MODEL_FILE = "data/experimental_isolation_forest.pkl"

print("Loading experimental dataset and trained model...")

# Load data
X = pd.read_csv(FEATURES_FILE)
labels = pd.read_csv(LABELS_FILE)

# Check row alignment
if len(X) != len(labels):
    raise ValueError("Feature and label row counts do not match.")

# Load saved model
saved_data = joblib.load(MODEL_FILE)

model = saved_data["model"]
feature_names = saved_data["feature_names"]

# Ensure the feature order is correct
X = X[feature_names]

# Recreate the same chronological test split
split_index = int(len(X) * 0.80)

X_test = X.iloc[split_index:].copy()
test_labels = labels.iloc[split_index:].copy()

# Actual labels: 0 = normal, 1 = anomaly
y_test = test_labels["is_anomaly"].astype(int)

# Predict: Isolation Forest returns 1 for normal, -1 for anomaly
raw_predictions = model.predict(X_test)

# Convert to 0 = normal, 1 = anomaly
y_pred = (raw_predictions == -1).astype(int)

# Combine results for category-wise analysis
results = test_labels.copy()
results["predicted_anomaly"] = y_pred

print("\nCATEGORY-WISE PERFORMANCE")
print("=" * 65)

categories = [
    "NORMAL",
    "HIGH_FREQUENCY",
    "UNUSUAL_TIMING",
    "UNUSUAL_PATIENT_PATTERN",
    "UNUSUAL_ACTION_PATTERN"
]

for category in categories:

    category_data = results[
        results["anomaly_type"] == category
    ]

    actual_count = len(category_data)

    if actual_count == 0:
        print(f"\n{category}: No test records found.")
        continue

    detected = int(category_data["predicted_anomaly"].sum())
    missed = actual_count - detected

    detection_rate = detected / actual_count

    print(f"\nCategory: {category}")
    print("-" * 40)
    print("Total records:", actual_count)
    print("Predicted as anomaly:", detected)
    print("Predicted as normal:", missed)
    print(f"Detection rate: {detection_rate:.2%}")

# Overall anomaly-category confusion matrix
print("\nOVERALL CONFUSION MATRIX")
print("=" * 65)

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=[0, 1]
)

print("Rows = Actual, Columns = Predicted")
print("Order: Normal (0), Anomaly (1)")
print(cm)

print("\nANALYSIS COMPLETED")
