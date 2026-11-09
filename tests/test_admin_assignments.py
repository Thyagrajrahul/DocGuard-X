
import pytest

from app import create_app
from app.database import db
from app.database.models import (
    User,
    Patient,
    Doctor,
    DoctorPatientAssignment
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

        # Create admin user
        admin_user = User(
            username="admin_test",
            email="admin_test@example.com",
            password_hash=hash_password("AdminTest123!"),
            role="admin",
            is_active=True
        )

        # Create doctor user
        doctor_user = User(
            username="doctor_test",
            email="doctor_test@example.com",
            password_hash=hash_password("DoctorTest123!"),
            role="doctor",
            is_active=True
        )

        db.session.add_all([admin_user, doctor_user])
        db.session.commit()

        # Create doctor profile
        doctor = Doctor(
            user_id=doctor_user.id,
            doctor_code="DOC100",
            full_name="Test Doctor",
            department="Cardiology",
            is_active=True
        )

        # Create patient
        patient = Patient(
            patient_code="PAT100",
            full_name="Test Patient",
            age=35,
            gender="Other",
            department="Cardiology",
            is_active=True
        )

        db.session.add_all([doctor, patient])
        db.session.commit()

        # Return simple integer IDs instead of database objects
        test_data = {
            "admin_user_id": admin_user.id,
            "doctor_user_id": doctor_user.id,
            "doctor_id": doctor.id,
            "patient_id": patient.id
        }

        return test_data


def login_user(client, username, password):
    response = client.post(
        "/login",
        json={
            "username": username,
            "password": password
        }
    )

    return response


def test_admin_can_assign_patient(app, setup_data):
    with app.app_context():

        client = app.test_client()

        login_response = login_user(
            client,
            "admin_test",
            "AdminTest123!"
        )

        assert login_response.status_code == 200

        doctor_id = setup_data["doctor_id"]
        patient_id = setup_data["patient_id"]

        response = client.post(
            "/admin/assignments",
            json={
                "doctor_id": doctor_id,
                "patient_id": patient_id
            }
        )

        assert response.status_code == 201

        assert response.get_json()["message"] == (
            "Patient assigned to doctor successfully"
        )

        assignment = DoctorPatientAssignment.query.first()

        assert assignment is not None
        assert assignment.doctor_id == doctor_id
        assert assignment.patient_id == patient_id
        assert assignment.is_active is True


def test_duplicate_assignment_is_rejected(app, setup_data):
    with app.app_context():

        client = app.test_client()

        login_user(
            client,
            "admin_test",
            "AdminTest123!"
        )

        doctor_id = setup_data["doctor_id"]
        patient_id = setup_data["patient_id"]

        # Create first assignment
        response1 = client.post(
            "/admin/assignments",
            json={
                "doctor_id": doctor_id,
                "patient_id": patient_id
            }
        )

        assert response1.status_code == 201

        # Try creating duplicate assignment
        response2 = client.post(
            "/admin/assignments",
            json={
                "doctor_id": doctor_id,
                "patient_id": patient_id
            }
        )

        assert response2.status_code == 409

        assert response2.get_json()["message"] == (
            "An active assignment already exists"
        )

        assert DoctorPatientAssignment.query.count() == 1


def test_doctor_cannot_access_admin_api(app, setup_data):
    with app.app_context():

        client = app.test_client()

        login_user(
            client,
            "doctor_test",
            "DoctorTest123!"
        )

        doctor_id = setup_data["doctor_id"]
        patient_id = setup_data["patient_id"]

        response = client.post(
            "/admin/assignments",
            json={
                "doctor_id": doctor_id,
                "patient_id": patient_id
            }
        )

        assert response.status_code == 403

        assert DoctorPatientAssignment.query.count() == 0


def test_admin_can_deactivate_assignment(app, setup_data):
    with app.app_context():

        client = app.test_client()

        login_user(
            client,
            "admin_test",
            "AdminTest123!"
        )

        doctor_id = setup_data["doctor_id"]
        patient_id = setup_data["patient_id"]

        # Create assignment
        response = client.post(
            "/admin/assignments",
            json={
                "doctor_id": doctor_id,
                "patient_id": patient_id
            }
        )

        assert response.status_code == 201

        assignment = DoctorPatientAssignment.query.first()
        assignment_id = assignment.id

        # Deactivate assignment
        deactivate_response = client.patch(
            f"/admin/assignments/{assignment_id}/deactivate"
        )

        assert deactivate_response.status_code == 200

        assert deactivate_response.get_json()["message"] == (
            "Assignment deactivated successfully"
        )

        # Fetch the assignment again from the database
        updated_assignment = db.session.get(
            DoctorPatientAssignment,
            assignment_id
        )

        assert updated_assignment.is_active is False

        
def test_admin_can_view_assignments(app, setup_data):
    with app.app_context():

        client = app.test_client()

        # Login as admin
        login_response = login_user(
            client,
            "admin_test",
            "AdminTest123!"
        )

        assert login_response.status_code == 200

        doctor_id = setup_data["doctor_id"]
        patient_id = setup_data["patient_id"]

        # Create assignment
        create_response = client.post(
            "/admin/assignments",
            json={
                "doctor_id": doctor_id,
                "patient_id": patient_id
            }
        )

        assert create_response.status_code == 201

        # View assignments
        response = client.get("/admin/assignments")

        assert response.status_code == 200

        data = response.get_json()

        assert "assignments" in data
        assert len(data["assignments"]) == 1

        assignment = data["assignments"][0]

        assert assignment["doctor_id"] == doctor_id
        assert assignment["patient_id"] == patient_id
        assert assignment["is_active"] is True

