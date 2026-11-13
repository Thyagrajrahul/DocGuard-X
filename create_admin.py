
from getpass import getpass

from app import create_app
from app.database import db
from app.database.models import User
from app.auth.security import hash_password


app = create_app()

with app.app_context():

    print("\n=== DocGuard-X Administrator Setup ===")

    username = input("Enter admin username: ").strip()
    email = input("Enter admin email: ").strip()
    password = getpass("Enter admin password: ")
    confirm_password = getpass("Confirm admin password: ")

    if not username or not email or not password:
        print("Error: All fields are required.")

    elif password != confirm_password:
        print("Error: Passwords do not match.")

    elif len(password) < 12:
        print("Error: Use a password with at least 12 characters.")

    else:
        existing_user = User.query.filter(
            (User.username == username) |
            (User.email == email)
        ).first()

        if existing_user:
            print("Error: Username or email already exists.")

        else:
            admin = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                role="admin",
                is_active=True
            )

            db.session.add(admin)
            db.session.commit()

            print("\nAdministrator account created successfully!")
            print("Username:", username)
            print("Role: admin")
            print("Account status: Active")
