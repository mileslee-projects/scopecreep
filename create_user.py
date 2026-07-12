# create_user.py — Run this once to create your account
# Usage: python3 create_user.py

from app import app, bcrypt
from models import db, User

EMAIL    = "mileslee1400@gmail.com"  # change if needed
PASSWORD = "changeme123"             # change to something secure

with app.app_context():
    db.create_all()

    existing = User.query.filter_by(email=EMAIL).first()
    if existing:
        print(f"User {EMAIL} already exists.")
    else:
        hashed = bcrypt.generate_password_hash(PASSWORD).decode("utf-8")
        user = User(email=EMAIL, password_hash=hashed)
        db.session.add(user)
        db.session.commit()
        print(f"Created user: {EMAIL}")
        print(f"Password: {PASSWORD}")
        print("Log in at http://127.0.0.1:5000/login")
