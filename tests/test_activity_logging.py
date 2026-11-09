
import pytest
from datetime import datetime, timezone

from app import create_app
from app.database import db
from app.database.models import (
    User,
    Patient,
    Doctor,
    DoctorPatientAssignment,
    ActivityLog,
    SecurityEvent
)
from app.auth.security import hash_password
from app.activity.logger import log_authorized_activity


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })

    with app.app_context():
        db.create_all()

        yield app

        db.session.remove()
        db.drop_all()


def test_activity_logging(app):
    with app.app_context():

        # Create a doctor user
        user = User(
            username="doctor1",
            email="doctor1@example.com",
            password_hash=hash_password("DoctorTest123!"),
            role="doctor",
            is_active=True
        )

        db.session.add(user)
        db.session.commit()

        # Create doctor profile
        doctor = Doctor(
            user_id=user.id,
            doctor_code="DOC001",
            full_name="Test Doctor",
            department="Cardiology",
            is_active=True
        )

        # Create patient
        patient = Patient(
            patient_code="PAT001",
            full_name="Test Patient",
            age=35,
            gender="Other",
            department="Cardiology",
            is_active=True
        )

        db.session.add_all([doctor, patient])
        db.session.commit()

        # Assign patient to doctor
        assignment = DoctorPatientAssignment(
            doctor_id=doctor.id,
            patient_id=patient.id,
            assigned_at=datetime.now(timezone.utc),
            valid_until=None,
            is_active=True
        )

        db.session.add(assignment)
        db.session.commit()

        # Test valid activity
        success, message = log_authorized_activity(
            user.id,
            patient.id,
            "VIEW"
        )

        assert success is True
        assert message == "Activity logged successfully"

        # Confirm authorized activity was saved
        assert ActivityLog.query.count() == 1

        activity = ActivityLog.query.first()

        assert activity.action == "VIEW"
        assert activity.doctor_id == doctor.id
        assert activity.patient_id == patient.id

        # Test unauthorized action
        success, message = log_authorized_activity(
            user.id,
            patient.id,
            "DELETE"
        )

        assert success is False
        assert message == "Invalid action"

        # Invalid action must not enter normal activity log
        assert ActivityLog.query.count() == 1

        # Invalid action must be recorded as a security event
        security_event = SecurityEvent.query.first()

        assert security_event is not None
        assert security_event.event_type == "INVALID_ACTION"
        assert security_event.action == "DELETE"


def test_unassigned_doctor_activity_is_rejected(app):
    with app.app_context():

        # Create doctor user
        user = User(
            username="doctor2",
            email="doctor2@example.com",
            password_hash=hash_password("DoctorTest123!"),
            role="doctor",
            is_active=True
        )

        db.session.add(user)
        db.session.commit()

        # Create doctor profile
        doctor = Doctor(
            user_id=user.id,
            doctor_code="DOC002",
            full_name="Unassigned Doctor",
            department="Neurology",
            is_active=True
        )

        # Create patient without assigning the patient to this doctor
        patient = Patient(
            patient_code="PAT002",
            full_name="Unassigned Patient",
            age=40,
            gender="Other",
            department="Neurology",
            is_active=True
        )

        db.session.add_all([doctor, patient])
        db.session.commit()

        # Attempt to access an unassigned patient
        success, message = log_authorized_activity(
            user.id,
            patient.id,
            "VIEW"
        )

        assert success is False
        assert message == "Doctor is not assigned to this patient"

        # No authorized activity should be created
        assert ActivityLog.query.count() == 0

        # Denied attempt should be recorded separately
        security_event = SecurityEvent.query.first()

        assert security_event is not None
        assert security_event.event_type == "ACCESS_DENIED"
        assert security_event.action == "VIEW"
