
import os

from flask import Flask, redirect

from app.database import db
from app.auth.routes import auth_bp
from app.admin.routes import admin_bp
from app.doctor.routes import doctor_bp

from app.database.models import (
    User,
    Patient,
    Doctor,
    DoctorPatientAssignment
)


def create_app(test_config=None):
    app = Flask(__name__)

    is_production = (
        os.environ.get("DOCGUARD_ENV", "development").lower()
        == "production"
    )

    secret_key = os.environ.get("DOCGUARD_SECRET_KEY")

    if not secret_key:
        if is_production:
            raise RuntimeError(
                "DOCGUARD_SECRET_KEY must be configured in production."
            )

        secret_key = "local-development-only-change-before-deployment"

    app.config.from_mapping(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI="sqlite:///docguard.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=is_production
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)

    @app.route("/")
    def home():
        return redirect("/login")

    return app
