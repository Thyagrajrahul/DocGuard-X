
import pytest

from app import create_app
from app.database import db
from app.database.models import User
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

        users = [
            User(
                username="admin_test",
                email="admin@example.com",
                password_hash=hash_password("AdminTest123!"),
                role="admin",
                is_active=True
            ),
            User(
                username="doctor_test",
                email="doctor@example.com",
                password_hash=hash_password("DoctorTest123!"),
                role="doctor",
                is_active=True
            )
        ]

        db.session.add_all(users)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password):
    return client.post(
        "/login",
        json={
            "username": username,
            "password": password
        }
    )


@pytest.fixture
def valid_event():
    return {
        "timestamp": "2024-03-30 11:38:51",
        "volume_kb": 7.41,
        "latency_ms": 26.8,
        "hospital_id": "ciming",
        "is_trusted_line": False,
        "dest_platform": "san_yi"
    }


def test_admin_can_analyze_traffic(client, valid_event):
    login(client, "admin_test", "AdminTest123!")

    response = client.post(
        "/admin/traffic/analyze",
        json=valid_event
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Traffic analysis completed"
    assert "prediction" in data["result"]
    assert "explanation" in data["result"]

    assert "classification" in data["result"]["prediction"]
    assert "indicators" in data["result"]["explanation"]


def test_doctor_cannot_analyze_traffic(client, valid_event):
    login(client, "doctor_test", "DoctorTest123!")

    response = client.post(
        "/admin/traffic/analyze",
        json=valid_event
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_analyze_traffic(
    client,
    valid_event
):
    response = client.post(
        "/admin/traffic/analyze",
        json=valid_event
    )

    assert response.status_code == 401


def test_missing_fields_are_rejected(client):
    login(client, "admin_test", "AdminTest123!")

    response = client.post(
        "/admin/traffic/analyze",
        json={
            "timestamp": "2024-03-30 11:38:51"
        }
    )

    assert response.status_code == 400
    assert "missing_fields" in response.get_json()


def test_invalid_event_data_is_rejected(client):
    login(client, "admin_test", "AdminTest123!")

    invalid_event = {
        "timestamp": "not-a-date",
        "volume_kb": 7.41,
        "latency_ms": 26.8,
        "hospital_id": "ciming",
        "is_trusted_line": False,
        "dest_platform": "san_yi"
    }

    response = client.post(
        "/admin/traffic/analyze",
        json=invalid_event
    )

    assert response.status_code == 400
