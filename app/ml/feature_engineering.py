import pandas as pd
from collections import defaultdict, deque

# File paths
INPUT_FILE = "data/experimental_activity.csv"
FEATURES_OUTPUT = "data/experimental_ml_features.csv"
LABELS_OUTPUT = "data/experimental_ml_labels.csv"


def create_features():
    print("Loading experimental activity dataset...")

    df = pd.read_csv(INPUT_FILE)

    # Convert timestamp into datetime format
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Sort records chronologically
    df = df.sort_values(
        by=["timestamp"],
        kind="stable"
    ).reset_index(drop=True)

    # Store historical events separately for each doctor
    doctor_history = defaultdict(deque)

    features = []
    labels = []

    print("Generating past-only historical features...")

    for _, row in df.iterrows():

        doctor_id = row["doctor_id"]
        patient_id = row["patient_id"]
        current_time = row["timestamp"]

        history = doctor_history[doctor_id]

        # Remove events older than 5 minutes
        while history and (
            current_time - history[0]["timestamp"]
        ).total_seconds() > 300:
            history.popleft()

        # Calculate features BEFORE adding current event
        previous_5min_count = len(history)

        previous_5min_unique_patients = len(
            set(event["patient_id"] for event in history)
        )

        if previous_5min_count > 0:
            previous_download_ratio = (
                sum(
                    1 for event in history
                    if event["action"] == "DOWNLOAD"
                ) / previous_5min_count
            )
        else:
            previous_download_ratio = 0.0

        # Time-based features
        activity_hour = current_time.hour
        day_of_week = current_time.day_of_week
        is_weekend = 1 if day_of_week >= 5 else 0

        features.append({
            "activity_hour": activity_hour,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "previous_5min_count": previous_5min_count,
            "previous_5min_unique_patients": previous_5min_unique_patients,
            "previous_download_ratio": previous_download_ratio
        })

        # Keep the label separate from model features
        labels.append({
            "is_anomaly": int(row["is_anomaly"]),
            "anomaly_type": row["anomaly_type"]
        })

        # Add current event to history only AFTER calculating features
        history.append({
            "timestamp": current_time,
            "patient_id": patient_id,
            "action": row["action"]
        })

    # Convert results into DataFrames
    features_df = pd.DataFrame(features)
    labels_df = pd.DataFrame(labels)

    # Save outputs
    features_df.to_csv(FEATURES_OUTPUT, index=False)
    labels_df.to_csv(LABELS_OUTPUT, index=False)

    print("\nFEATURE ENGINEERING COMPLETED")
    print("--------------------------------")
    print("Total records:", len(features_df))
    print("Total features:", len(features_df.columns))
    print("Missing feature values:", features_df.isnull().sum().sum())

    print("\nFeature columns:")
    print(features_df.columns.tolist())

    print("\nAnomaly distribution:")
    print(labels_df["anomaly_type"].value_counts())

    print("\nSaved files:")
    print(FEATURES_OUTPUT)
    print(LABELS_OUTPUT)


if __name__ == "__main__":
    create_features()