
import pytest
from datetime import datetime, timedelta, timezone

from app import create_app
from app.database import db
from app.database.models import (
    User,
    Patient,
    Doctor,
    DoctorPatientAssignment
)
from app.authorization.authorization import check_patient_access
from app.auth.security import hash_password


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


@pytest.fixture
def setup_data(app):
    # The app fixture keeps its application context active.
    doctor_user = User(
        username="doctor1",
        email="doctor@test.com",
        password_hash=hash_password("test123"),
        role="doctor",
        is_active=True
    )

    inactive_user = User(
        username="inactive1",
        email="inactive@test.com",
        password_hash=hash_password("test123"),
        role="doctor",
        is_active=False
    )

    unassigned_user = User(
        username="doctor2",
        email="unassigned@test.com",
        password_hash=hash_password("test123"),
        role="doctor",
        is_active=True
    )

    patient = Patient(
        patient_code="PAT001",
        full_name="Test Patient",
        age=35,
        gender="Other",
        department="General"
    )

    db.session.add_all([
        doctor_user,
        inactive_user,
        unassigned_user,
        patient
    ])

    db.session.flush()

    doctor = Doctor(
        user_id=doctor_user.id,
        doctor_code="DOC001",
        full_name="Assigned Doctor",
        department="General"
    )

    unassigned_doctor = Doctor(
        user_id=unassigned_user.id,
        doctor_code="DOC002",
        full_name="Unassigned Doctor",
        department="General"
    )

    db.session.add_all([doctor, unassigned_doctor])
    db.session.flush()

    assignment = DoctorPatientAssignment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        assigned_at=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=None,
        is_active=True
    )

    db.session.add(assignment)
    db.session.commit()

    return {
        "doctor_user_id": doctor_user.id,
        "inactive_user_id": inactive_user.id,
        "unassigned_user_id": unassigned_user.id,
        "patient_id": patient.id,
        "assignment_id": assignment.id
    }


def test_assigned_doctor_gets_access(app, setup_data):
    allowed, message = check_patient_access(
        setup_data["doctor_user_id"],
        setup_data["patient_id"]
    )

    assert allowed is True
    assert message == "Access granted"


def test_unassigned_doctor_is_denied(app, setup_data):
    allowed, message = check_patient_access(
        setup_data["unassigned_user_id"],
        setup_data["patient_id"]
    )

    assert allowed is False
    assert message == "Doctor is not assigned to this patient"


def test_inactive_doctor_account_is_denied(app, setup_data):
    allowed, message = check_patient_access(
        setup_data["inactive_user_id"],
        setup_data["patient_id"]
    )

    assert allowed is False
    assert message == "User account is invalid or inactive"


def test_expired_assignment_is_denied(app, setup_data):
    assignment = db.session.get(
        DoctorPatientAssignment,
        setup_data["assignment_id"]
    )

    assignment.valid_until = datetime.now(timezone.utc) - timedelta(days=1)
    db.session.commit()

    allowed, message = check_patient_access(
        setup_data["doctor_user_id"],
        setup_data["patient_id"]
    )

    assert allowed is False
    assert message == "Doctor assignment has expired"


def test_admin_cannot_access_patient(app, setup_data):
    admin = User(
        username="admin1",
        email="admin@test.com",
        password_hash=hash_password("test123"),
        role="admin",
        is_active=True
    )
    db.session.add(admin)
    db.session.commit()

    allowed, message = check_patient_access(
        admin.id,
        setup_data["patient_id"]
    )

    assert allowed is False
    assert message == "Only doctors can access patient records"


def test_nonexistent_user_is_denied(app, setup_data):
    allowed, message = check_patient_access(
        99999,
        setup_data["patient_id"]
    )

    assert allowed is False
    assert message == "User account is invalid or inactive"


def test_nonexistent_patient_is_denied(app, setup_data):
    allowed, message = check_patient_access(
        setup_data["doctor_user_id"],
        99999
    )

    assert allowed is False
    assert message == "Patient record is invalid or inactive"


def test_inactive_patient_is_denied(app, setup_data):
    patient = db.session.get(
        Patient,
        setup_data["patient_id"]
    )
    patient.is_active = False
    db.session.commit()

    allowed, message = check_patient_access(
        setup_data["doctor_user_id"],
        setup_data["patient_id"]
    )

    assert allowed is False
    assert message == "Patient record is invalid or inactive"


def test_inactive_doctor_profile_is_denied(app, setup_data):
    doctor = Doctor.query.filter_by(
        user_id=setup_data["doctor_user_id"]
    ).first()

    doctor.is_active = False
    db.session.commit()

    allowed, message = check_patient_access(
        setup_data["doctor_user_id"],
        setup_data["patient_id"]
    )

    assert allowed is False
    assert message == "Active doctor profile not found"


def test_future_assignment_is_denied(app, setup_data):
    assignment = db.session.get(
        DoctorPatientAssignment,
        setup_data["assignment_id"]
    )

    assignment.assigned_at = (
        datetime.now(timezone.utc) + timedelta(days=1)
    )
    db.session.commit()

    allowed, message = check_patient_access(
        setup_data["doctor_user_id"],
        setup_data["patient_id"]
    )

    assert allowed is False
    assert message == "Assignment is not yet valid"
