
import pandas as pd
import pickle

from sklearn.metrics import precision_score, recall_score, f1_score

# Load test features and labels
X = pd.read_csv("data/revised_ml_features.csv")
labels = pd.read_csv("data/revised_ml_labels.csv")

# Recreate the same chronological test split
split_index = int(len(X) * 0.80)

X_test = X.iloc[split_index:]
y_test = labels.iloc[split_index:]

# Load the previously trained model
with open("data/revised_isolation_forest.pkl", "rb") as file:
    saved_data = pickle.load(file)

model = saved_data["model"]

# Check that the feature order matches training
expected_features = saved_data["feature_columns"]

if X_test.columns.tolist() != expected_features:
    raise ValueError("Feature columns do not match the trained model.")

# Predict test records
predictions = model.predict(X_test)
y_pred = (predictions == -1).astype(int)

# Build category-wise report
results = []

for category in sorted(y_test["anomaly_type"].unique()):

    # Identify records belonging to this category
    category_mask = y_test["anomaly_type"] == category

    actual = y_test.loc[category_mask, "is_anomaly"]
    predicted = y_pred[category_mask.to_numpy()]

    results.append({
        "Category": category,
        "Records": len(actual),
        "Detected": int(predicted.sum()),
        "Missed": int(((actual == 1) & (predicted == 0)).sum()),
        "Precision": round(
            precision_score(actual, predicted, zero_division=0), 3
        ),
        "Recall": round(
            recall_score(actual, predicted, zero_division=0), 3
        ),
        "F1 Score": round(
            f1_score(actual, predicted, zero_division=0), 3
        )
    })

report = pd.DataFrame(results)

print("CATEGORY-WISE MODEL PERFORMANCE")
print(report.to_string(index=False))
