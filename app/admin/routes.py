from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, render_template

from app.database import db
from app.database.models import (
    Doctor,
    Patient,
    DoctorPatientAssignment,
    SecurityEvent
)

from app.auth.decorators import role_required
from app.ml.predict_traffic import analyze_traffic_event
from app.ml.batch_analysis import analyze_dataset_batch


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# --------------------------------------------------
# 1. Admin Dashboard
# --------------------------------------------------

@admin_bp.route("/dashboard", methods=["GET"])
@role_required("admin")
def admin_dashboard():

    total_doctors = Doctor.query.filter_by(
        is_active=True
    ).count()

    total_patients = Patient.query.filter_by(
        is_active=True
    ).count()

    active_assignments = DoctorPatientAssignment.query.filter_by(
        is_active=True
    ).count()

    total_security_events = SecurityEvent.query.count()

    recent_security_events = SecurityEvent.query.order_by(
        SecurityEvent.timestamp.desc()
    ).limit(10).all()

    return render_template(
        "admin/dashboard.html",
        total_doctors=total_doctors,
        total_patients=total_patients,
        active_assignments=active_assignments,
        total_security_events=total_security_events,
        recent_security_events=recent_security_events
    )


# --------------------------------------------------
# 2. Assign a patient to a doctor
# --------------------------------------------------

@admin_bp.route("/assignments", methods=["POST"])
@role_required("admin")
def assign_patient():

    data = request.get_json(silent=True) or {}

    doctor_id = data.get("doctor_id")
    patient_id = data.get("patient_id")
    valid_until_input = data.get("valid_until")

    if not doctor_id or not patient_id:
        return jsonify({
            "message": "Doctor ID and Patient ID are required"
        }), 400

    doctor = db.session.get(Doctor, doctor_id)
    patient = db.session.get(Patient, patient_id)

    if doctor is None or patient is None:
        return jsonify({
            "message": "Doctor or patient not found"
        }), 404

    if not doctor.is_active or not patient.is_active:
        return jsonify({
            "message": "Inactive doctors or patients cannot be assigned"
        }), 400

    existing_assignment = DoctorPatientAssignment.query.filter_by(
        doctor_id=doctor_id,
        patient_id=patient_id,
        is_active=True
    ).first()

    if existing_assignment:
        return jsonify({
            "message": "An active assignment already exists"
        }), 409

    valid_until = None

    if valid_until_input:
        try:
            valid_until = datetime.fromisoformat(
                valid_until_input
            )
        except (ValueError, TypeError):
            return jsonify({
                "message": "Invalid expiration date"
            }), 400

        if valid_until <= datetime.now():
            return jsonify({
                "message": "Expiration date must be in the future"
            }), 400

    assignment = DoctorPatientAssignment(
        doctor_id=doctor_id,
        patient_id=patient_id,
        assigned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        valid_until=valid_until,
        is_active=True
    )

    try:
        db.session.add(assignment)
        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "message": "Patient assigned to doctor successfully",
        "assignment_id": assignment.id
    }), 201


# --------------------------------------------------
# 3. View doctor-patient assignments
# --------------------------------------------------

@admin_bp.route("/assignments", methods=["GET"])
@role_required("admin")
def list_assignments():

    assignments = DoctorPatientAssignment.query.all()

    result = []

    for assignment in assignments:

        result.append({
            "id": assignment.id,
            "doctor_id": assignment.doctor_id,
            "patient_id": assignment.patient_id,
            "is_active": assignment.is_active,
            "assigned_at": (
                assignment.assigned_at.isoformat()
                if assignment.assigned_at
                else None
            ),
            "valid_until": (
                assignment.valid_until.isoformat()
                if assignment.valid_until
                else None
            )
        })

    return jsonify({
        "assignments": result
    }), 200


# --------------------------------------------------
# 4. Deactivate a doctor-patient assignment
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

    assignment.is_active = False

    db.session.commit()

    return jsonify({
        "message": "Assignment deactivated successfully"
    }), 200


# --------------------------------------------------
# 5. Analyze healthcare traffic using AI
# --------------------------------------------------

@admin_bp.route("/traffic/analyze", methods=["POST"])
@role_required("admin")
def analyze_healthcare_traffic():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "message": "A valid JSON event is required"
        }), 400

    required_fields = [
        "timestamp",
        "volume_kb",
        "latency_ms",
        "hospital_id",
        "is_trusted_line",
        "dest_platform"
    ]

    missing_fields = [
        field for field in required_fields
        if field not in data
    ]

    if missing_fields:
        return jsonify({
            "message": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    try:
        result = analyze_traffic_event(data)

    except (ValueError, TypeError):
        return jsonify({
            "message": "Invalid traffic event data"
        }), 400

    except FileNotFoundError:
        return jsonify({
            "message": "Trained AI model is unavailable"
        }), 503

    return jsonify({
        "message": "Traffic analysis completed",
        "result": result
    }), 200


# --------------------------------------------------
# 6. Batch analysis using downloaded dataset
# --------------------------------------------------

@admin_bp.route("/traffic/batch-analyze", methods=["POST"])
@role_required("admin")
def analyze_traffic_dataset():

    data = request.get_json(silent=True) or {}

    max_records = data.get("max_records", 1000)
    threshold_strategy = data.get(
        "threshold_strategy",
        "best_f1"
    )

    if (
        isinstance(max_records, bool)
        or not isinstance(max_records, int)
    ):
        return jsonify({
            "message": "max_records must be an integer"
        }), 400

    if threshold_strategy not in [
        "best_f1",
        "lower_fpr"
    ]:
        return jsonify({
            "message": "Invalid threshold strategy"
        }), 400

    try:
        result = analyze_dataset_batch(
            max_records=max_records,
            threshold_strategy=threshold_strategy
        )

    except (ValueError, TypeError) as error:
        return jsonify({
            "message": str(error)
        }), 400

    except FileNotFoundError:
        return jsonify({
            "message": "Dataset or trained model not found"
        }), 503

    return jsonify({
        "message": "Dataset batch analysis completed",
        "result": result
    }), 200