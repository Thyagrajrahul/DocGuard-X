
import pandas as pd
import random
from datetime import datetime, timedelta

# ==================================================
# 1. CONFIGURATION
# ==================================================

random.seed(42)

NUM_DOCTORS = 20
NUM_NORMAL = 3000
ANOMALIES_PER_CATEGORY = 100

OUTPUT_FILE = "data/experimental_activity.csv"

DEPARTMENTS = [
    "Cardiology",
    "Neurology",
    "Orthopedics",
    "General Medicine"
]

ACTIONS = ["VIEW", "UPDATE", "DOWNLOAD"]
ACTION_WEIGHTS = [0.75, 0.15, 0.10]

START_DATE = datetime(2026, 1, 1)
TOTAL_DAYS = 90


# ==================================================
# 2. CREATE DOCTORS
# ==================================================

doctors = {}

for doctor_id in range(1, NUM_DOCTORS + 1):

    doctors[doctor_id] = {
        "department": random.choice(DEPARTMENTS),
        "preferred_hour": random.randint(8, 16)
    }


# ==================================================
# 3. CREATE PATIENTS
# ==================================================

patients = {}

for patient_id in range(1, 301):

    assigned_doctor = random.choice(list(doctors.keys()))

    patients[patient_id] = {
        "department": doctors[assigned_doctor]["department"]
    }


# ==================================================
# 4. HELPER FUNCTIONS
# ==================================================

def random_timestamp():
    """Generate a timestamp across the 90-day period."""

    day = random.randint(0, TOTAL_DAYS - 1)
    hour = random.randint(6, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return START_DATE + timedelta(
        days=day,
        hours=hour,
        minutes=minute,
        seconds=second
    )


def choose_action():
    """Choose an action using normal action probabilities."""

    return random.choices(
        ACTIONS,
        weights=ACTION_WEIGHTS
    )[0]


def choose_patient(
    doctor_id,
    cross_department_probability=0.25
):
    """
    Select a patient based on the doctor's department.

    cross_department_probability controls the chance
    of selecting a patient from another department.
    """

    doctor_department = doctors[doctor_id]["department"]

    if random.random() < cross_department_probability:

        other_patients = [
            patient_id
            for patient_id, details in patients.items()
            if details["department"] != doctor_department
        ]

        return random.choice(other_patients)

    same_department_patients = [
        patient_id
        for patient_id, details in patients.items()
        if details["department"] == doctor_department
    ]

    return random.choice(same_department_patients)


def create_record(
    doctor_id,
    patient_id,
    timestamp,
    action,
    anomaly_type="NORMAL"
):
    """Create one activity record."""

    doctor_department = doctors[doctor_id]["department"]
    patient_department = patients[patient_id]["department"]

    return {
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "timestamp": timestamp,
        "action": action,
        "doctor_department": doctor_department,
        "patient_department": patient_department,
        "is_assigned": True,
        "anomaly_type": anomaly_type,
        "is_anomaly": int(anomaly_type != "NORMAL")
    }


# ==================================================
# 5. GENERATE NORMAL ACTIVITIES
# ==================================================

records = []

for _ in range(NUM_NORMAL):

    doctor_id = random.choice(list(doctors.keys()))

    patient_id = choose_patient(
        doctor_id,
        cross_department_probability=0.25
    )

    timestamp = random_timestamp()

    # Doctors usually work around their preferred hours.
    # Occasional after-hours activity is also possible.

    if random.random() < 0.65:

        preferred_hour = doctors[doctor_id]["preferred_hour"]

        hour = int(random.gauss(preferred_hour, 2.5))
        hour = max(6, min(23, hour))

        timestamp = timestamp.replace(hour=hour)

    action = choose_action()

    records.append(
        create_record(
            doctor_id,
            patient_id,
            timestamp,
            action
        )
    )


# ==================================================
# 6. UNUSUAL TIMING ACTIVITIES
# ==================================================

for _ in range(ANOMALIES_PER_CATEGORY):

    doctor_id = random.choice(list(doctors.keys()))

    patient_id = choose_patient(
        doctor_id,
        cross_department_probability=0.25
    )

    timestamp = random_timestamp()

    # Most events occur outside common working hours.
    # Some still occur during normal working hours.

    if random.random() < 0.75:

        unusual_hour = random.choice(
            list(range(0, 6)) + list(range(22, 24))
        )

        timestamp = timestamp.replace(hour=unusual_hour)

    records.append(
        create_record(
            doctor_id,
            patient_id,
            timestamp,
            choose_action(),
            "UNUSUAL_TIMING"
        )
    )


# ==================================================
# 7. HIGH-FREQUENCY ACTIVITIES
# ==================================================

for _ in range(ANOMALIES_PER_CATEGORY):

    doctor_id = random.choice(list(doctors.keys()))

    patient_id = choose_patient(
        doctor_id,
        cross_department_probability=0.25
    )

    timestamp = random_timestamp()

    # Vary the number of events and time intervals.

    burst_size = random.randint(3, 8)
    interval_seconds = random.randint(20, 100)

    for event_number in range(burst_size):

        event_time = timestamp + timedelta(
            seconds=event_number * interval_seconds
        )

        records.append(
            create_record(
                doctor_id,
                patient_id,
                event_time,
                choose_action(),
                "HIGH_FREQUENCY"
            )
        )


# ==================================================
# 8. UNUSUAL PATIENT PATTERNS
# ==================================================

for _ in range(ANOMALIES_PER_CATEGORY):

    doctor_id = random.choice(list(doctors.keys()))

    # Higher probability of cross-department access.
    patient_id = choose_patient(
        doctor_id,
        cross_department_probability=0.75
    )

    timestamp = random_timestamp()

    records.append(
        create_record(
            doctor_id,
            patient_id,
            timestamp,
            choose_action(),
            "UNUSUAL_PATIENT_PATTERN"
        )
    )


# ==================================================
# 9. UNUSUAL ACTION PATTERNS
# ==================================================

for _ in range(ANOMALIES_PER_CATEGORY):

    doctor_id = random.choice(list(doctors.keys()))

    patient_id = choose_patient(
        doctor_id,
        cross_department_probability=0.25
    )

    timestamp = random_timestamp()

    # Downloads are more frequent in this category,
    # but VIEW and UPDATE are still possible.

    action = random.choices(
        ACTIONS,
        weights=[0.25, 0.15, 0.60]
    )[0]

    records.append(
        create_record(
            doctor_id,
            patient_id,
            timestamp,
            action,
            "UNUSUAL_ACTION_PATTERN"
        )
    )


# ==================================================
# 10. CREATE AND SORT DATASET
# ==================================================

df = pd.DataFrame(records)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values(
    "timestamp"
).reset_index(drop=True)


# ==================================================
# 11. SAVE DATASET
# ==================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ==================================================
# 12. DISPLAY DATASET SUMMARY
# ==================================================

print("\nEXPERIMENTAL DATASET GENERATED")

print("\nTotal records:", len(df))

print("\nAnomaly distribution:")
print(df["anomaly_type"].value_counts())

print("\nMissing values:", df.isnull().sum().sum())

print("\nOutput file:", OUTPUT_FILE)

print("\nDataset shape:", df.shape)

print("\nAction distribution:")
print(df["action"].value_counts())

print("\nDepartment mismatch distribution:")

department_mismatch = (
    df["doctor_department"] != df["patient_department"]
)

print(
    df.groupby("anomaly_type")
    .apply(
        lambda group: (
            group["doctor_department"]
            != group["patient_department"]
        ).mean(),
        include_groups=False
    )
    .round(3)
)

print("\nDataset generation completed successfully!")
