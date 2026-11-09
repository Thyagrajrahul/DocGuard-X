
import pandas as pd

features = pd.read_csv("data/revised_ml_features.csv")
labels = pd.read_csv("data/revised_ml_labels.csv")

df = features.copy()
df["is_anomaly"] = labels["is_anomaly"]

print("FEATURE COMPARISON")
print("\nNormal vs Anomaly averages:\n")

print(
    df.groupby("is_anomaly")
    .mean(numeric_only=True)
    .round(3)
    .T
)

print("\nFEATURE RANGES:\n")

for column in features.columns:
    print(f"\n{column}")
    print("Minimum:", features[column].min())
    print("Maximum:", features[column].max())
