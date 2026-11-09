
import pandas as pd

labels = pd.read_csv("data/revised_ml_labels.csv")

split_index = int(len(labels) * 0.80)

train_labels = labels.iloc[:split_index]
test_labels = labels.iloc[split_index:]

print("TRAINING ANOMALY DISTRIBUTION")
print(train_labels["anomaly_type"].value_counts())

print("\nTESTING ANOMALY DISTRIBUTION")
print(test_labels["anomaly_type"].value_counts())

print("\nTRAINING ANOMALY PERCENTAGE:")
print(round(train_labels["is_anomaly"].mean() * 100, 2), "%")

print("\nTESTING ANOMALY PERCENTAGE:")
print(round(test_labels["is_anomaly"].mean() * 100, 2), "%")
