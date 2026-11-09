
from datetime import datetime, timezone

from app.database import db
from app.database.models import (
    User,
    Doctor,
    Patient,
    DoctorPatientAssignment
)


def check_patient_access(user_id, patient_id):

    # 1. Check whether the user exists and is active
    user = db.session.get(User, user_id)

    if user is None or not user.is_active:
        return False, "User account is invalid or inactive"

    # 2. Check whether the user is a doctor
    if user.role != "doctor":
        return False, "Only doctors can access patient records"

    # 3. Find the doctor's profile
    doctor = Doctor.query.filter_by(
        user_id=user.id,
        is_active=True
    ).first()

    if doctor is None:
        return False, "Active doctor profile not found"

    # 4. Check whether the patient exists and is active
    patient = db.session.get(Patient, patient_id)

    if patient is None or not patient.is_active:
        return False, "Patient record is invalid or inactive"

    # 5. Check the doctor's assignment
    assignment = DoctorPatientAssignment.query.filter_by(
        doctor_id=doctor.id,
        patient_id=patient.id,
        is_active=True
    ).first()

    if assignment is None:
        return False, "Doctor is not assigned to this patient"

    # 6. Check assignment validity
    now = datetime.now(timezone.utc)

    assigned_at = assignment.assigned_at.replace(
        tzinfo=timezone.utc
    )

    if assigned_at > now:
        return False, "Assignment is not yet valid"

    if assignment.valid_until is not None:
        expiry = assignment.valid_until.replace(
            tzinfo=timezone.utc
        )

        if expiry <= now:
            return False, "Doctor assignment has expired"

    return True, "Access granted"
