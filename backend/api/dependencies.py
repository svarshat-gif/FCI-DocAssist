from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database.session import get_db
from models.user import User
from utils.config import get_settings
from utils.security import decode_access_token

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_prefix}/auth/login",
    auto_error=False,
)

DbSession = Annotated[Session, Depends(get_db)]


def get_optional_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User | None:
    if not token:
        return None
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Session is no longer active.")
    return user


def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )
    return user


def get_request_id(request: Request) -> str:
    return request.headers.get("x-request-id", "local-request")
