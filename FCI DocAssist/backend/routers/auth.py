from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import DbSession, get_current_user
from models.schemas import Token, UserCreate, UserLogin, UserRead
from models.user import User
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(payload: UserCreate, db: DbSession) -> Token:
    user, token = AuthService(db).register(payload)
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: DbSession) -> Token:
    user, token = AuthService(db).authenticate(payload.email, payload.password)
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user
