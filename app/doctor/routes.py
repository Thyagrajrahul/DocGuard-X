
from flask import Blueprint, jsonify, session, render_template

from app.database import db
from app.database.models import (
    Patient,
    Doctor,
    DoctorPatientAssignment
)
from app.auth.decorators import role_required
from app.authorization.authorization import check_patient_access
from app.activity.logger import log_authorized_activity


doctor_bp = Blueprint(
    "doctor",
    __name__,
    url_prefix="/doctor"
)


# --------------------------------------------------
# 1. Doctor Dashboard
# --------------------------------------------------

@doctor_bp.route("/dashboard", methods=["GET"])
@role_required("doctor")
def doctor_dashboard():

    user_id = session.get("user_id")

    doctor = Doctor.query.filter_by(
        user_id=user_id,
        is_active=True
    ).first()

    if doctor is None:
        return jsonify({
            "message": "Active doctor profile not found"
        }), 403

    assignments = DoctorPatientAssignment.query.filter_by(
        doctor_id=doctor.id,
        is_active=True
    ).all()

    assigned_patients = []

    for assignment in assignments:

        allowed, message = check_patient_access(
            user_id,
            assignment.patient_id
        )

        if allowed:
            patient = db.session.get(
                Patient,
                assignment.patient_id
            )

            if patient is not None:
                assigned_patients.append(patient)

    return render_template(
        "doctor/dashboard.html",
        doctor=doctor,
        patients=assigned_patients
    )


# --------------------------------------------------
# 2. View Patient Record
# --------------------------------------------------


@doctor_bp.route(
    "/patients/<int:patient_id>",
    methods=["GET"]
)
@role_required("doctor")
def view_patient(patient_id):

    user_id = session.get("user_id")

    # Step 1: Check authorization
    allowed, message = check_patient_access(
        user_id,
        patient_id
    )

    if not allowed:

        # Logger records the denied attempt exactly once
        log_authorized_activity(
            user_id,
            patient_id,
            "VIEW"
        )

        return jsonify({
            "message": message
        }), 403

    # Step 2: Retrieve the patient record
    patient = db.session.get(Patient, patient_id)

    if patient is None:
        return jsonify({
            "message": "Patient not found"
        }), 404

    # Step 3: Log authorized activity
    success, message = log_authorized_activity(
        user_id,
        patient_id,
        "VIEW"
    )

    if not success:
        return jsonify({
            "message": message
        }), 403

    # Step 4: Return patient information
    return jsonify({
        "message": "Patient record accessed successfully",
        "patient": {
            "patient_id": patient.id,
            "patient_code": patient.patient_code,
            "full_name": patient.full_name,
            "age": patient.age,
            "gender": patient.gender,
            "department": patient.department
        }
    }), 200
