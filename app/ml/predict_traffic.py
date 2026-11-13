
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


# Locate the project directory independently of the terminal location.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "data"
    / "final_model"
    / "docguard_final_model.joblib"
)


@lru_cache(maxsize=1)
def load_model_artifact():
    """
    Load the trained model and fitted preprocessor once.

    Only load model artifacts created and trusted by this project.
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found: {MODEL_PATH}"
        )

    artifact = joblib.load(MODEL_PATH)

    required_keys = {
        "model_name",
        "model",
        "preprocessor",
        "numeric_features",
        "categorical_features",
        "best_f1_threshold",
        "recall_threshold"
    }

    missing_keys = required_keys - set(artifact.keys())

    if missing_keys:
        raise ValueError(
            f"Model artifact is missing keys: {missing_keys}"
        )

    return artifact


def convert_to_boolean(value):
    """Convert common boolean representations safely."""

    if isinstance(value, (bool, np.bool_)):
        return bool(value)

    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in ("true", "1", "yes"):
            return True

        if normalized in ("false", "0", "no"):
            return False

    raise ValueError(
        "is_trusted_line must be True, False, 1, or 0."
    )


def predict_traffic_event(event, threshold_strategy="best_f1"):
    """
    Analyse one healthcare traffic event.

    Required event fields:
        timestamp
        volume_kb
        latency_ms
        hospital_id
        is_trusted_line
        dest_platform

    threshold_strategy:
        best_f1  - selected using validation F1
        lower_fpr - selected using validation FPR constraint
    """

    required_fields = {
        "timestamp",
        "volume_kb",
        "latency_ms",
        "hospital_id",
        "is_trusted_line",
        "dest_platform"
    }

    if not isinstance(event, dict):
        raise TypeError("Event must be supplied as a dictionary.")

    missing = required_fields - set(event.keys())

    if missing:
        raise ValueError(
            f"Missing event fields: {sorted(missing)}"
        )

    artifact = load_model_artifact()

    # Select the threshold stored in the trained artifact.
    if threshold_strategy == "best_f1":
        threshold = artifact["best_f1_threshold"]

    elif threshold_strategy == "lower_fpr":
        threshold = artifact["recall_threshold"]

        if threshold is None:
            raise ValueError(
                "The lower-FPR threshold is not available."
            )

    else:
        raise ValueError(
            "threshold_strategy must be 'best_f1' or 'lower_fpr'."
        )

    # Parse event timestamp.
    timestamp = pd.to_datetime(
        event["timestamp"],
        errors="raise"
    )

    # Convert numeric values.
    volume_kb = float(event["volume_kb"])
    latency_ms = float(event["latency_ms"])

    if not np.isfinite(volume_kb) or not np.isfinite(latency_ms):
        raise ValueError(
            "volume_kb and latency_ms must be finite numbers."
        )

    # Convert trusted-line value to the same string format
    # used during model training.
    trusted_line = str(
        convert_to_boolean(event["is_trusted_line"])
    )

    # Reconstruct the original eight model input features.
    feature_row = {
        "volume_kb": volume_kb,
        "latency_ms": latency_ms,
        "hour": timestamp.hour,
        "day_of_week": timestamp.day_of_week,
        "month": timestamp.month,
        "hospital_id": str(event["hospital_id"]),
        "is_trusted_line": trusted_line,
        "dest_platform": str(event["dest_platform"])
    }

    numeric_features = artifact["numeric_features"]
    categorical_features = artifact["categorical_features"]

    feature_columns = numeric_features + categorical_features

    input_df = pd.DataFrame(
        [feature_row],
        columns=feature_columns
    )

    # Apply the exact fitted preprocessing used during training.
    processed_features = artifact["preprocessor"].transform(
        input_df
    )

    # Get the model's estimated anomaly probability.
    anomaly_probability = float(
        artifact["model"].predict_proba(
            processed_features
        )[0][1]
    )

    # Classify using the selected threshold.
    is_anomaly = anomaly_probability >= threshold

    return {
        "model_name": artifact["model_name"],
        "anomaly_probability": round(
            anomaly_probability, 6
        ),
        "threshold": round(float(threshold), 6),
        "threshold_strategy": threshold_strategy,
        "is_anomaly": bool(is_anomaly),
        "classification": (
            "Potential Anomaly"
            if is_anomaly
            else "Normal"
        )
    }


def analyze_traffic_event(event, threshold_strategy="best_f1"):
    """
    Combine model prediction with rule-based explanations.
    """

    from app.explanations.traffic_explainer import (
        explain_traffic_event
    )

    prediction = predict_traffic_event(
        event,
        threshold_strategy=threshold_strategy
    )

    explanation = explain_traffic_event(event)

    return {
        "prediction": prediction,
        "explanation": explanation
    }
