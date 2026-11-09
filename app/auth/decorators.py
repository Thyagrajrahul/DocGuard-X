
from functools import wraps
from flask import session, jsonify


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "message": "Please log in first"
            }), 401

        return func(*args, **kwargs)

    return wrapper


def role_required(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({
                    "message": "Please log in first"
                }), 401

            if session.get("role") != required_role:
                return jsonify({
                    "message": "Access denied"
                }), 403

            return func(*args, **kwargs)

        return wrapper

    return decorator
