
import csv
import random

from datetime import datetime, timedelta


# Reproducible dataset generation
random.seed(42)


# Output file
OUTPUT_FILE = "data/revised_activity.csv"


# Dataset settings
NUM_DOCTORS = 20
NUM_NORMAL_RECORDS = 3000
ANOMALY_RECORDS_PER_TYPE = 100


DEPARTMENTS = [
    "Cardiology",
    "Neurology",
    "Orthopedics",
    "General"
]

ACTIONS = [
    "VIEW",
    "UPDATE",
    "DOWNLOAD"
]


# Each doctor has an assigned department
DOCTOR_DEPARTMENTS = {
    doctor_id: random.choice(DEPARTMENTS)
    for doctor_id in range(1, NUM_DOCTORS + 1)
}


def random_working_timestamp():
    """Generate a timestamp during normal working hours."""

    day = random.randint(0, 89)

    hour = random.randint(8, 17)

    minute = random.randint(0, 59)

    second = random.randint(0, 59)

    return datetime(
        2026, 1, 1, hour, minute, second
    ) + timedelta(days=day)


def create_record(
    doctor_id,
    patient_id,
    timestamp,
    doctor_department,
    patient_department,
    action,
    anomaly_type
):

    return {
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "timestamp": timestamp.isoformat(),
        "action": action,
        "doctor_department": doctor_department,
        "patient_department": patient_department,
        "is_assigned": True,
        "anomaly_type": anomaly_type,
        "is_anomaly": 0 if anomaly_type == "NORMAL" else 1
    }


def generate_normal_records():

    records = []

    for _ in range(NUM_NORMAL_RECORDS):

        doctor_id = random.randint(1, NUM_DOCTORS)

        doctor_department = DOCTOR_DEPARTMENTS[doctor_id]

        # Most doctors access patients from their own department.
        patient_department = doctor_department

        # Generate normal timestamps.
        timestamp = random_working_timestamp()

        # Different doctors have different action preferences.
        action = random.choices(
            ACTIONS,
            weights=[75, 15, 10],
            k=1
        )[0]

        records.append(
            create_record(
                doctor_id,
                random.randint(1001, 1300),
                timestamp,
                doctor_department,
                patient_department,
                action,
                "NORMAL"
            )
        )

    return records


def generate_unusual_timing_records():

    records = []

    for _ in range(ANOMALY_RECORDS_PER_TYPE):

        doctor_id = random.randint(1, NUM_DOCTORS)

        doctor_department = DOCTOR_DEPARTMENTS[doctor_id]

        # Generate unusual working times.
        hour = random.choice(
            [0, 1, 2, 3, 4, 5, 22, 23]
        )

        timestamp = datetime(
            2026,
            random.randint(1, 3),
            random.randint(1, 28),
            hour,
            random.randint(0, 59),
            random.randint(0, 59)
        )

        records.append(
            create_record(
                doctor_id,
                random.randint(1001, 1300),
                timestamp,
                doctor_department,
                doctor_department,
                random.choice(ACTIONS),
                "UNUSUAL_TIMING"
            )
        )

    return records


def generate_high_frequency_records():

    records = []

    for group in range(ANOMALY_RECORDS_PER_TYPE // 10):

        doctor_id = random.randint(1, NUM_DOCTORS)

        doctor_department = DOCTOR_DEPARTMENTS[doctor_id]

        start_time = datetime(
            2026,
            random.randint(1, 3),
            random.randint(1, 28),
            random.randint(9, 16),
            0,
            0
        )

        # Generate a burst of activity.
        for index in range(10):

            timestamp = start_time + timedelta(
                seconds=index * 20
            )

            records.append(
                create_record(
                    doctor_id,
                    random.randint(1001, 1300),
                    timestamp,
                    doctor_department,
                    doctor_department,
                    random.choice(ACTIONS),
                    "HIGH_FREQUENCY"
                )
            )

    return records


def generate_unusual_patient_records():

    records = []

    for _ in range(ANOMALY_RECORDS_PER_TYPE):

        doctor_id = random.randint(1, NUM_DOCTORS)

        doctor_department = DOCTOR_DEPARTMENTS[doctor_id]

        other_departments = [
            department
            for department in DEPARTMENTS
            if department != doctor_department
        ]

        patient_department = random.choice(other_departments)

        records.append(
            create_record(
                doctor_id,
                random.randint(1001, 1300),
                random_working_timestamp(),
                doctor_department,
                patient_department,
                random.choice(ACTIONS),
                "UNUSUAL_PATIENT_PATTERN"
            )
        )

    return records


def generate_unusual_action_records():

    records = []

    for _ in range(ANOMALY_RECORDS_PER_TYPE):

        doctor_id = random.randint(1, NUM_DOCTORS)

        doctor_department = DOCTOR_DEPARTMENTS[doctor_id]

        # Unusually high proportion of DOWNLOAD activity.
        records.append(
            create_record(
                doctor_id,
                random.randint(1001, 1300),
                random_working_timestamp(),
                doctor_department,
                doctor_department,
                "DOWNLOAD",
                "UNUSUAL_ACTION_PATTERN"
            )
        )

    return records


def generate_dataset():

    records = []

    # Generate normal activity
    records.extend(
        generate_normal_records()
    )

    # Generate unusual activity
    records.extend(
        generate_unusual_timing_records()
    )

    records.extend(
        generate_high_frequency_records()
    )

    records.extend(
        generate_unusual_patient_records()
    )

    records.extend(
        generate_unusual_action_records()
    )

    # Sort chronologically
    records.sort(
        key=lambda record: record["timestamp"]
    )

    fieldnames = [
        "doctor_id",
        "patient_id",
        "timestamp",
        "action",
        "doctor_department",
        "patient_department",
        "is_assigned",
        "anomaly_type",
        "is_anomaly"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(records)

    print("\nREVISED DATASET GENERATED")
    print("-----------------------------")

    print("Total records:", len(records))

    print("Normal records:", sum(
        record["is_anomaly"] == 0
        for record in records
    ))

    print("Anomaly records:", sum(
        record["is_anomaly"] == 1
        for record in records
    ))

    print("\nANOMALY CATEGORY COUNTS")

    for category in [
        "UNUSUAL_TIMING",
        "HIGH_FREQUENCY",
        "UNUSUAL_PATIENT_PATTERN",
        "UNUSUAL_ACTION_PATTERN"
    ]:

        count = sum(
            record["anomaly_type"] == category
            for record in records
        )

        print(category + ":", count)

    print("\nOutput file:", OUTPUT_FILE)


if __name__ == "__main__":
    generate_dataset()
