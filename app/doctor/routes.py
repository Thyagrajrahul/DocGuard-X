
from flask import Blueprint, jsonify, session

from app.database import db
from app.database.models import Patient
from app.auth.decorators import role_required
from app.authorization.authorization import check_patient_access
from app.activity.logger import log_authorized_activity


doctor_bp = Blueprint(
    "doctor",
    __name__,
    url_prefix="/doctor"
)


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

        # Record the denied access as a security event
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

    # Step 3: Log activity after successful retrieval
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
