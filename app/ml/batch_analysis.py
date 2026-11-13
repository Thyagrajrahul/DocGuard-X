from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score

from app.ml.predict_traffic import (
    load_model_artifact,
    convert_to_boolean
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    PROJECT_ROOT
    / "dataset"
    / "lecheng_security_logs_2024H1_pipeline10.csv"
)


REQUIRED_COLUMNS = [
    "timestamp",
    "hospital_id",
    "volume_kb",
    "latency_ms",
    "risk_label",
    "is_trusted_line",
    "dest_platform"
]


def analyze_dataset_batch(
    max_records=5000,
    threshold_strategy="best_f1"
):
    """
    Analyze a limited number of CSV records using the
    existing trained model.

    Ground-truth labels are used only after prediction
    to calculate evaluation metrics.
    """

    if not isinstance(max_records, int) or not 1 <= max_records <= 20000:
        raise ValueError(
            "max_records must be between 1 and 20000."
        )

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    artifact = load_model_artifact()

    if threshold_strategy == "best_f1":
        threshold = float(artifact["best_f1_threshold"])

    elif threshold_strategy == "lower_fpr":
        threshold_value = artifact["recall_threshold"]

        if threshold_value is None:
            raise ValueError(
                "The lower-FPR threshold is unavailable."
            )

        threshold = float(threshold_value)

    else:
        raise ValueError(
            "Invalid threshold strategy."
        )

    # Check the CSV columns before processing.
    available_columns = pd.read_csv(
        DATASET_PATH,
        nrows=0
    ).columns.tolist()

    missing_columns = (
        set(REQUIRED_COLUMNS) - set(available_columns)
    )

    if missing_columns:
        raise ValueError(
            f"Dataset is missing columns: {sorted(missing_columns)}"
        )

    all_probabilities = []
    all_predictions = []
    all_actual_labels = []
    sample_records = []

    records_analyzed = 0

    numeric_features = artifact["numeric_features"]
    categorical_features = artifact["categorical_features"]

    feature_columns = (
        numeric_features + categorical_features
    )

    # Read only a limited number of rows in small chunks.
    chunks = pd.read_csv(
        DATASET_PATH,
        chunksize=1000,
        nrows=max_records
    )

    for chunk in chunks:

        timestamps = pd.to_datetime(
            chunk["timestamp"],
            errors="coerce"
        )

        if timestamps.isna().any():
            raise ValueError(
                "Dataset contains invalid timestamps."
            )

        volume = pd.to_numeric(
            chunk["volume_kb"],
            errors="coerce"
        )

        latency = pd.to_numeric(
            chunk["latency_ms"],
            errors="coerce"
        )

        if (
            volume.isna().any()
            or latency.isna().any()
            or not np.isfinite(volume).all()
            or not np.isfinite(latency).all()
        ):
            raise ValueError(
                "Dataset contains invalid numeric traffic values."
            )

        if chunk[
            ["hospital_id", "dest_platform", "is_trusted_line"]
        ].isna().any().any():
            raise ValueError(
                "Dataset contains missing model input values."
            )

        trusted_values = chunk[
            "is_trusted_line"
        ].map(convert_to_boolean).astype(str)

        # Construct exactly the same features used
        # by the single-event prediction function.
        feature_data = {
            "volume_kb": volume.astype(float).to_numpy(),
            "latency_ms": latency.astype(float).to_numpy(),
            "hour": timestamps.dt.hour.to_numpy(),
            "day_of_week": timestamps.dt.day_of_week.to_numpy(),
            "month": timestamps.dt.month.to_numpy(),
            "hospital_id": chunk["hospital_id"].astype(str).to_numpy(),
            "is_trusted_line": trusted_values.to_numpy(),
            "dest_platform": chunk["dest_platform"].astype(str).to_numpy()
        }

        input_df = pd.DataFrame(
            feature_data,
            columns=feature_columns
        )

        # Use the fitted preprocessing pipeline.
        processed_features = artifact["preprocessor"].transform(
            input_df
        )

        model = artifact["model"]

        probabilities = model.predict_proba(
            processed_features
        )

        classes = list(model.classes_)

        if 1 not in classes:
            raise ValueError(
                "The trained model does not contain anomaly class 1."
            )

        anomaly_class_index = classes.index(1)

        batch_probabilities = probabilities[
            :, anomaly_class_index
        ]

        batch_predictions = (
            batch_probabilities >= threshold
        ).astype(int)

        actual_labels = pd.to_numeric(
            chunk["risk_label"],
            errors="coerce"
        )

        if (
            actual_labels.isna().any()
            or not actual_labels.isin([0, 1]).all()
        ):
            raise ValueError(
                "risk_label must contain only 0 or 1."
            )

        all_probabilities.extend(
            batch_probabilities.tolist()
        )

        all_predictions.extend(
            batch_predictions.tolist()
        )

        all_actual_labels.extend(
            actual_labels.astype(int).tolist()
        )

        # Keep a small number of records for dashboard display.
        for position in range(len(chunk)):

            sample_records.append({
                "timestamp": str(
                    chunk.iloc[position]["timestamp"]
                ),
                "hospital_id": str(
                    chunk.iloc[position]["hospital_id"]
                ),
                "volume_kb": float(volume.iloc[position]),
                "latency_ms": float(latency.iloc[position]),
                "is_trusted_line": bool(
                    trusted_values.iloc[position] == "True"
                ),
                "dest_platform": str(
                    chunk.iloc[position]["dest_platform"]
                ),
                "anomaly_probability": round(
                    float(batch_probabilities[position]), 6
                ),
                "classification": (
                    "Potential Anomaly"
                    if batch_predictions[position] == 1
                    else "Normal"
                ),
                "actual_label": int(
                    actual_labels.iloc[position]
                )
            })

        records_analyzed += len(chunk)

    if records_analyzed == 0:
        raise ValueError(
            "No dataset records were available for analysis."
        )

    predictions_array = np.array(all_predictions)
    actual_array = np.array(all_actual_labels)

    tn, fp, fn, tp = confusion_matrix(
        actual_array,
        predictions_array,
        labels=[0, 1]
    ).ravel()

    false_positive_rate = (
        float(fp / (fp + tn))
        if (fp + tn) > 0
        else 0.0
    )

    # Select the highest-probability records for review.
    sample_records.sort(
        key=lambda item: item["anomaly_probability"],
        reverse=True
    )

    top_records = sample_records[:10]

    from app.explanations.traffic_explainer import (
        explain_traffic_event
    )

    for record in top_records:
        explanation = explain_traffic_event(record)
        record["explanation"] = explanation["indicators"]

    return {
        "dataset": DATASET_PATH.name,
        "records_analyzed": records_analyzed,
        "model_name": artifact["model_name"],
        "threshold_strategy": threshold_strategy,
        "threshold": round(threshold, 6),
        "normal_count": int(
            np.sum(predictions_array == 0)
        ),
        "anomaly_count": int(
            np.sum(predictions_array == 1)
        ),
        "evaluation": {
            "precision": round(
                float(precision_score(
                    actual_array,
                    predictions_array,
                    zero_division=0
                )),
                4
            ),
            "recall": round(
                float(recall_score(
                    actual_array,
                    predictions_array,
                    zero_division=0
                )),
                4
            ),
            "f1_score": round(
                float(f1_score(
                    actual_array,
                    predictions_array,
                    zero_division=0
                )),
                4
            ),
            "false_positive_rate": round(
                false_positive_rate,
                4
            ),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        },
        "highest_risk_records": top_records
    }