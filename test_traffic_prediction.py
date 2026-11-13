
import pandas as pd

from app.ml.predict_traffic import predict_traffic_event


df = pd.read_csv(
    "dataset/lecheng_security_logs_2024H1_pipeline10.csv"
)

# Select one normal event and one known anomaly.
normal_row = df[df["risk_label"] == 0].iloc[0]
anomaly_row = df[df["risk_label"] == 1].iloc[0]


def display_event(row, description):
    event = {
        "timestamp": row["timestamp"],
        "volume_kb": row["volume_kb"],
        "latency_ms": row["latency_ms"],
        "hospital_id": row["hospital_id"],
        "is_trusted_line": row["is_trusted_line"],
        "dest_platform": row["dest_platform"]
    }

    result = predict_traffic_event(event)

    print(f"\n{description}")
    print("Dataset ground truth:", int(row["risk_label"]))
    print("Model prediction:", result["classification"])
    print("Anomaly probability:", result["anomaly_probability"])
    print("Threshold:", result["threshold"])


display_event(normal_row, "NORMAL EVENT")
display_event(anomaly_row, "KNOWN ANOMALY EVENT")
