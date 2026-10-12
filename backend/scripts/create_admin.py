"""Create a reserved administrator account without putting its password in arguments."""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from database.init_db import init_db
from database.session import SessionLocal
from models.schemas import UserCreate
from models.user import User
from utils.config import get_settings
from utils.security import get_password_hash


def main():
    allowed = {email.lower() for email in get_settings().crawler_admin_emails}
    email = input("Administrator email: ").strip().lower()
    if email not in allowed:
        raise SystemExit("This address is not in CRAWLER_ADMIN_EMAILS.")
    password = getpass.getpass("New password (at least 12 characters): ")
    if len(password) < 12 or password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords must match and contain at least 12 characters.")
    payload = UserCreate(email=email, password=password, full_name="Administrator")
    init_db()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Account already exists. No password was changed.")
        db.add(User(email=payload.email, full_name=payload.full_name, hashed_password=get_password_hash(password)))
        db.commit()
    print("Administrator account created. Sign in with your email and password.")


if __name__ == "__main__":
    main()
