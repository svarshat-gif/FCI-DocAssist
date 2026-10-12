from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.schemas import UserCreate
from models.user import User
from utils.security import create_access_token, get_password_hash, verify_password
from utils.config import get_settings


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, payload: UserCreate) -> tuple[User, str]:
        settings = get_settings()
        if settings.environment == "production" and payload.email.lower() in {email.lower() for email in settings.crawler_admin_emails}:
            raise HTTPException(status_code=403, detail="This account must be set up by the administrator.")
        existing = self.db.scalar(select(User).where(User.email == payload.email.lower()))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name,
            hashed_password=get_password_hash(payload.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user, create_access_token(user.id)

    def authenticate(self, email: str, password: str) -> tuple[User, str]:
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is disabled.",
            )
        return user, create_access_token(user.id)
