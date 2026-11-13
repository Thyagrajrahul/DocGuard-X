
def explain_traffic_event(event):
    """
    Generate human-readable indicators for a healthcare
    traffic event.

    These are rule-based observations, not SHAP explanations
    or proof of malicious activity.
    """

    indicators = []

    volume = float(event["volume_kb"])
    latency = float(event["latency_ms"])
    trusted = event["is_trusted_line"]

    if volume > 1000:
        indicators.append(
            "Unusually large data volume was observed."
        )

    if latency > 500:
        indicators.append(
            "High network latency was observed."
        )

    if not trusted:
        indicators.append(
            "The event originated from an untrusted network line."
        )

    if not indicators:
        indicators.append(
            "No predefined high-risk indicators were detected."
        )

    return {
        "indicators": indicators,
        "explanation_type": "Rule-based observations",
        "warning": (
            "These indicators do not prove malicious activity."
        )
    }
