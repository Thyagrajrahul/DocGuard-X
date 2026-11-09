
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from app.database import db
from app.database.models import (
    User,
    Doctor,
    Patient,
    ActivityLog,
    SecurityEvent
)
from app.authorization.authorization import check_patient_access


ALLOWED_ACTIONS = {"VIEW", "UPDATE", "DOWNLOAD"}


def record_security_event(user_id, patient_id, event_type, action, reason):

    # Only store IDs that actually exist in the database
    existing_user = db.session.get(User, user_id)
    existing_patient = db.session.get(Patient, patient_id)

    event = SecurityEvent(
        user_id=existing_user.id if existing_user else None,
        patient_id=existing_patient.id if existing_patient else None,
        event_type=event_type,
        action=str(action)[:50],
        reason=reason[:255],
        timestamp=datetime.now(timezone.utc)
    )

    try:
        db.session.add(event)
        db.session.commit()
        return True

    except SQLAlchemyError:
        db.session.rollback()
        return False


def log_authorized_activity(user_id, patient_id, action):

    # 1. Validate the requested action
    if not isinstance(action, str):
        action = "UNKNOWN"
        record_security_event(
            user_id,
            patient_id,
            "INVALID_ACTION",
            action,
            "Action must be a valid string"
        )
        return False, "Invalid action"

    action = action.strip().upper()

    if action not in ALLOWED_ACTIONS:
        record_security_event(
            user_id,
            patient_id,
            "INVALID_ACTION",
            action,
            "Unsupported action requested"
        )
        return False, "Invalid action"

    # 2. Check whether the doctor is authorized
    allowed, message = check_patient_access(user_id, patient_id)

    if not allowed:
        record_security_event(
            user_id,
            patient_id,
            "ACCESS_DENIED",
            action,
            message
        )
        return False, message

    # 3. Find the doctor's profile
    doctor = Doctor.query.filter_by(
        user_id=user_id,
        is_active=True
    ).first()

    if doctor is None:
        record_security_event(
            user_id,
            patient_id,
            "ACCESS_DENIED",
            action,
            "Active doctor profile not found"
        )
        return False, "Active doctor profile not found"

    # 4. Create the authorized activity record
    activity = ActivityLog(
        doctor_id=doctor.id,
        patient_id=patient_id,
        action=action,
        timestamp=datetime.now(timezone.utc),
        department=doctor.department
    )

    # 5. Save the authorized activity
    try:
        db.session.add(activity)
        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        return False, "Could not save activity"

    return True, "Activity logged successfully"
