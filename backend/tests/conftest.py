import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["SCHEDULER_ENABLED"] = "false"

from database.base import Base
from models import circular, conversation, user  # noqa: F401


@compiles(JSONB, "sqlite")
def compile_test_json(_type, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


@pytest.fixture
def users(db):
    from models.user import User
    from utils.security import get_password_hash
    first = User(email="first@example.com", hashed_password=get_password_hash("password-123"))
    second = User(email="second@example.com", hashed_password=get_password_hash("password-456"))
    db.add_all([first, second])
    db.commit()
    return first, second


@pytest.fixture
def ai(monkeypatch):
    from services import chat_service
    retriever = Mock()
    retriever.retrieve.return_value = []
    generator = Mock()
    monkeypatch.setattr(chat_service, "Retriever", lambda *_: retriever)
    monkeypatch.setattr(chat_service, "GeminiService", lambda: generator)
    return retriever, generator


@pytest.fixture
def client(db, ai, monkeypatch):
    from fastapi.testclient import TestClient
    import main
    from database.session import get_db
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main, "start_scheduler", lambda: None)
    main.app.dependency_overrides[get_db] = lambda: db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
