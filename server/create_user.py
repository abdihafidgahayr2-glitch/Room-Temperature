"""Create the first login (there is no public sign-up page on purpose).

Usage:  uv run python create_user.py
"""
import getpass
import sys

from sqlalchemy import select

import models
from auth import hash_password
from database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)

username = input("Username: ").strip()
email = input("Email: ").strip()
password = getpass.getpass("Password (min 10 characters): ")
if len(password) < 10:
    sys.exit("Password must be at least 10 characters.")
if password != getpass.getpass("Repeat password: "):
    sys.exit("Passwords don't match.")

with SessionLocal() as db:
    result = db.execute(select(models.User).where(models.User.username == username))
    if result.scalars().first():
        sys.exit("Username already exists.")
    result = db.execute(select(models.User).where(models.User.email == email))
    if result.scalars().first():
        sys.exit("Email already exists.")
    new_user = models.User(username=username, email=email, password_hash=hash_password(password))
    db.add(new_user)
    db.commit()

print(f"Created user '{username}'.")
