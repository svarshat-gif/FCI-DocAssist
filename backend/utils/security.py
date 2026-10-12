from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
import bcrypt
import hashlib

from utils.config import get_settings

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if hashed_password.startswith("bcrypt-sha256$"):
            digest = hashlib.sha256(plain_password.encode("utf-8")).hexdigest().encode("ascii")
            return bcrypt.checkpw(digest, hashed_password.split("$", 1)[1].encode("ascii"))
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("ascii"))
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    # Prehash to avoid bcrypt's 72-byte password truncation, including Unicode input.
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")
    return "bcrypt-sha256$" + bcrypt.hashpw(digest, bcrypt.gensalt()).decode("ascii")


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
