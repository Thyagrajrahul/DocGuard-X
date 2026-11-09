
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
    with app.app_context():

        # Create doctor user
        doctor_user = User(
            username="doctor_access",
            email="doctor_access@example.com",
            password_hash=hash_password("DoctorTest123!"),
            role="doctor",
            is_active=True
        )

        # Create admin user
        admin_user = User(
            username="admin_access",
            email="admin_access@example.com",
            password_hash=hash_password("AdminTest123!"),
            role="admin",
            is_active=True
        )

        # Create another doctor user who is not assigned
        unassigned_user = User(
            username="doctor_unassigned",
            email="unassigned@example.com",
            password_hash=hash_password("DoctorTest456!"),
            role="doctor",
            is_active=True
        )

        db.session.add_all([
            doctor_user,
            admin_user,
            unassigned_user
        ])
        db.session.commit()

        # Create doctor profiles
        doctor = Doctor(
            user_id=doctor_user.id,
            doctor_code="DOC201",
            full_name="Assigned Test Doctor",
            department="Cardiology",
            is_active=True
        )

        unassigned_doctor = Doctor(
            user_id=unassigned_user.id,
            doctor_code="DOC202",
            full_name="Unassigned Test Doctor",
            department="Neurology",
            is_active=True
        )

        # Create patient
        patient = Patient(
            patient_code="PAT201",
            full_name="Synthetic Test Patient",
            age=35,
            gender="Other",
            department="Cardiology",
            is_active=True
        )

        db.session.add_all([
            doctor,
            unassigned_doctor,
            patient
        ])
        db.session.commit()

        # Assign patient only to the first doctor
        assignment = DoctorPatientAssignment(
            doctor_id=doctor.id,
            patient_id=patient.id,
            assigned_at=datetime.now(timezone.utc),
            valid_until=None,
            is_active=True
        )

        db.session.add(assignment)
        db.session.commit()

        return {
            "doctor_user_id": doctor_user.id,
            "admin_user_id": admin_user.id,
            "unassigned_user_id": unassigned_user.id,
            "doctor_id": doctor.id,
            "patient_id": patient.id
        }


def login_user(client, username, password):
    return client.post(
        "/login",
        json={
            "username": username,
            "password": password
        }
    )


def test_assigned_doctor_can_view_patient(app, setup_data):
    with app.app_context():

        client = app.test_client()

        login_response = login_user(
            client,
            "doctor_access",
            "DoctorTest123!"
        )

        assert login_response.status_code == 200

        patient_id = setup_data["patient_id"]

        response = client.get(
            f"/doctor/patients/{patient_id}"
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["message"] == (
            "Patient record accessed successfully"
        )

        assert data["patient"]["patient_id"] == patient_id
        assert data["patient"]["patient_code"] == "PAT201"

        # Successful access should be logged
        assert ActivityLog.query.count() == 1

        activity = ActivityLog.query.first()

        assert activity.action == "VIEW"


def test_unassigned_doctor_cannot_view_patient(app, setup_data):
    with app.app_context():

        client = app.test_client()

        login_response = login_user(
            client,
            "doctor_unassigned",
            "DoctorTest456!"
        )

        assert login_response.status_code == 200

        patient_id = setup_data["patient_id"]

        response = client.get(
            f"/doctor/patients/{patient_id}"
        )

        assert response.status_code == 403

        assert response.get_json()["message"] == (
            "Doctor is not assigned to this patient"
        )

        # Denied access must not enter normal activity logs
        assert ActivityLog.query.count() == 0

        # Denied access should create a security event
        security_event = SecurityEvent.query.first()

        assert security_event is not None
        assert security_event.event_type == "ACCESS_DENIED"


def test_admin_cannot_use_doctor_api(app, setup_data):
    with app.app_context():

        client = app.test_client()

        login_response = login_user(
            client,
            "admin_access",
            "AdminTest123!"
        )

        assert login_response.status_code == 200

        patient_id = setup_data["patient_id"]

        response = client.get(
            f"/doctor/patients/{patient_id}"
        )

        assert response.status_code == 403

        assert ActivityLog.query.count() == 0


def test_unauthenticated_user_cannot_view_patient(app, setup_data):
    with app.app_context():

        client = app.test_client()

        patient_id = setup_data["patient_id"]

        response = client.get(
            f"/doctor/patients/{patient_id}"
        )

        assert response.status_code == 401

        assert ActivityLog.query.count() == 0
