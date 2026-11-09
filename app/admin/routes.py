
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from app.database import db
from app.database.models import (
    Doctor,
    Patient,
    DoctorPatientAssignment
)
from app.auth.decorators import role_required


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# --------------------------------------------------
# 1. Assign a patient to a doctor
# --------------------------------------------------

@admin_bp.route("/assignments", methods=["POST"])
@role_required("admin")
def assign_patient():

    data = request.get_json(silent=True) or {}

    doctor_id = data.get("doctor_id")
    patient_id = data.get("patient_id")
    valid_until_input = data.get("valid_until")

    # Validate required IDs
    if doctor_id is None or patient_id is None:
        return jsonify({
            "message": "Doctor ID and Patient ID are required"
        }), 400

    # Validate ID types
    if (
        not isinstance(doctor_id, int)
        or isinstance(doctor_id, bool)
        or not isinstance(patient_id, int)
        or isinstance(patient_id, bool)
    ):
        return jsonify({
            "message": "Doctor ID and Patient ID must be integers"
        }), 400

    # Check doctor
    doctor = db.session.get(Doctor, doctor_id)

    if doctor is None or not doctor.is_active:
        return jsonify({
            "message": "Doctor not found or inactive"
        }), 404

    # Check patient
    patient = db.session.get(Patient, patient_id)

    if patient is None or not patient.is_active:
        return jsonify({
            "message": "Patient not found or inactive"
        }), 404

    # Check for existing active assignment
    existing_assignment = DoctorPatientAssignment.query.filter_by(
        doctor_id=doctor.id,
        patient_id=patient.id,
        is_active=True
    ).first()

    if existing_assignment is not None:
        return jsonify({
            "message": "An active assignment already exists"
        }), 409

    # Parse optional assignment expiry date
    valid_until = None

    if valid_until_input:

        if not isinstance(valid_until_input, str):
            return jsonify({
                "message": "Valid-until must be an ISO date string"
            }), 400

        try:
            valid_until = datetime.fromisoformat(
                valid_until_input.replace("Z", "+00:00")
            )

            if valid_until.tzinfo is None:
                valid_until = valid_until.replace(
                    tzinfo=timezone.utc
                )

            valid_until = valid_until.astimezone(timezone.utc)

        except ValueError:
            return jsonify({
                "message": "Invalid valid-until date format"
            }), 400

        if valid_until <= datetime.now(timezone.utc):
            return jsonify({
                "message": "Valid-until must be in the future"
            }), 400

    # Create assignment
    assignment = DoctorPatientAssignment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        assigned_at=datetime.now(timezone.utc),
        valid_until=valid_until,
        is_active=True
    )

    try:
        db.session.add(assignment)
        db.session.commit()

    except Exception:
        db.session.rollback()

        return jsonify({
            "message": "Could not create assignment"
        }), 500

    return jsonify({
        "message": "Patient assigned to doctor successfully",
        "assignment_id": assignment.id,
        "doctor_id": doctor.id,
        "patient_id": patient.id
    }), 201


# --------------------------------------------------
# 2. View all assignments
# --------------------------------------------------

@admin_bp.route("/assignments", methods=["GET"])
@role_required("admin")
def get_assignments():

    assignments = DoctorPatientAssignment.query.order_by(
        DoctorPatientAssignment.id.desc()
    ).all()

    assignment_list = []

    for assignment in assignments:

        assignment_list.append({
            "assignment_id": assignment.id,
            "doctor_id": assignment.doctor_id,
            "patient_id": assignment.patient_id,
            "assigned_at": assignment.assigned_at.isoformat(),
            "valid_until": (
                assignment.valid_until.isoformat()
                if assignment.valid_until
                else None
            ),
            "is_active": assignment.is_active
        })

    return jsonify({
        "assignments": assignment_list
    }), 200


# --------------------------------------------------
# 3. Deactivate an assignment
# --------------------------------------------------

@admin_bp.route(
    "/assignments/<int:assignment_id>/deactivate",
    methods=["PATCH"]
)
@role_required("admin")
def deactivate_assignment(assignment_id):

    assignment = db.session.get(
        DoctorPatientAssignment,
        assignment_id
    )

    if assignment is None:
        return jsonify({
            "message": "Assignment not found"
        }), 404

    if not assignment.is_active:
        return jsonify({
            "message": "Assignment is already inactive"
        }), 409

    assignment.is_active = False

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()

        return jsonify({
            "message": "Could not deactivate assignment"
        }), 500

    return jsonify({
        "message": "Assignment deactivated successfully"
    }), 200
