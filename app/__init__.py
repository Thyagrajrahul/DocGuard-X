
from flask import Flask
from app.doctor.routes import doctor_bp

from app.database import db
from app.database.models import (
    User,
    Patient,
    Doctor,
    DoctorPatientAssignment
)
from app.auth.routes import auth_bp
from app.admin.routes import admin_bp


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        SECRET_KEY="dev-only-change-this-before-deployment",
        SQLALCHEMY_DATABASE_URI="sqlite:///docguard.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    # Apply test settings BEFORE initializing the database
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)

    @app.route("/")
    def home():
        return "Welcome to DocGuard-X!"

    return app
