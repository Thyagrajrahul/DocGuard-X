from app.auth.decorators import login_required, role_required
from flask import Blueprint, request, jsonify, session
from app.database.models import User
from app.database import db
from app.auth.security import verify_password

auth_bp = Blueprint("auth", __name__)
@auth_bp.route("/login", methods=["GET"])
def login_page():
    from flask import render_template
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()

    if user is None or not user.is_active:
        return jsonify({"message": "Invalid username or password"}), 401

    if not verify_password(user.password_hash, password):
        return jsonify({"message": "Invalid username or password"}), 401

    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role

    return jsonify({
        "message": "Login successful",
        "role": user.role
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200
@auth_bp.route("/admin-only")
@role_required("admin")
def admin_only():
    return jsonify({"message": "Admin access granted"}), 200


@auth_bp.route("/doctor-only")
@role_required("doctor")
def doctor_only():
    return jsonify({"message": "Doctor access granted"}), 200