from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from models.document_vector import DocumentVector
from models.schemas import UserCreate
from utils.config import Settings
from utils.text import TextChunk, chunk_pages


def cloud_settings(**kwargs):
    return Settings(_env_file=None, embedding_provider="gemini", vector_store="postgres", **kwargs)


def test_postgres_storage_expiry_replacement_and_rollback(db, monkeypatch):
    from rag import postgres_store
    monkeypatch.setattr(postgres_store, "get_settings", cloud_settings)
    store = postgres_store.PostgresVectorStore(db)
    chunk = TextChunk("Public circular text", 1, 3)
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    store.upsert_temp_chunks("upload_private", "sample.pdf", [chunk], [[1.0] * 768], expiry)
    db.commit()
    assert store.count("upload_private") == 1
    assert store.count() == 0
    store.upsert_temp_chunks("upload_private", "updated.pdf", [chunk], [[2.0] * 768], expiry)
    assert db.scalar(select(DocumentVector)).source_metadata["title"] == "updated.pdf"
    db.rollback()
    assert db.scalar(select(DocumentVector)).source_metadata["title"] == "sample.pdf"
    vector = db.scalar(select(DocumentVector))
    vector.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert store.count("upload_private") == 0
    store.delete_collection("upload_private")
    db.commit()
    assert db.scalar(select(DocumentVector)) is None


def test_postgres_cap_and_query_scope(db, monkeypatch):
    from rag import postgres_store
    monkeypatch.setattr(postgres_store, "get_settings", lambda: cloud_settings(max_stored_chunks=100))
    store = postgres_store.PostgresVectorStore(db)
    chunks = [TextChunk("Text", 1, 1)] * 101
    with pytest.raises(HTTPException) as error:
        store.upsert_temp_chunks("upload_test", "sample.pdf", chunks, [[1.0] * 768] * 101)
    assert error.value.status_code == 507
    assert store.count("upload_test") == 0
    statement = store.query_statement([1.0] * 768, "upload_private").compile(dialect=postgresql.dialect())
    assert "<=>" in str(statement)
    assert "expires_at" in str(statement)
    assert "upload_private" in statement.params.values()
    assert store.model in statement.params.values()


def test_gemini_embedding_batches_and_normalization(monkeypatch):
    from embeddings import gemini_embedder
    monkeypatch.setattr(gemini_embedder, "get_settings", lambda: cloud_settings(gemini_api_key="test-only", embedding_batch_size=2))
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.embed_content.side_effect = lambda **kwargs: SimpleNamespace(
        embeddings=[SimpleNamespace(values=[2.0] * 768) for _ in kwargs["contents"]]
    )
    monkeypatch.setattr(gemini_embedder.genai, "Client", lambda **_: client)
    result = gemini_embedder.GeminiEmbedder().embed_documents(["one", "two", "three"])
    assert len(result) == 3
    assert sum(value * value for value in result[0]) == pytest.approx(1)
    assert client.models.embed_content.call_count == 2
    assert client.models.embed_content.call_args.kwargs["config"].task_type == "RETRIEVAL_DOCUMENT"


@pytest.mark.parametrize("values", [[0.0] * 768, [1.0], [float("nan")] * 768])
def test_malformed_gemini_embeddings_fail_closed(monkeypatch, values):
    from embeddings import gemini_embedder
    monkeypatch.setattr(gemini_embedder, "get_settings", lambda: cloud_settings(gemini_api_key="test-only"))
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.embed_content.return_value = SimpleNamespace(embeddings=[SimpleNamespace(values=values)])
    monkeypatch.setattr(gemini_embedder.genai, "Client", lambda **_: client)
    with pytest.raises(HTTPException) as error:
        gemini_embedder.GeminiEmbedder().embed_query("public text")
    assert error.value.status_code == 502


def test_upload_consent_and_public_policy(client, users, monkeypatch):
    from routers import uploads, health
    from utils.security import create_access_token
    monkeypatch.setattr(uploads, "get_settings", cloud_settings)
    monkeypatch.setattr(health, "get_settings", cloud_settings)
    service = MagicMock(side_effect=AssertionError("Must not process without consent"))
    monkeypatch.setattr(uploads, "UploadService", service)
    response = client.post("/api/v1/uploads/pdf", headers={"Authorization": f"Bearer {create_access_token(users[0].id)}"}, files={"file": ("test.pdf", b"%PDF-test", "application/pdf")})
    assert response.status_code == 400
    service.assert_not_called()
    policy = client.get("/api/v1/health/upload-policy").json()
    assert policy["google_processing"] is True
    assert set(policy) == {"google_processing", "max_upload_mb", "expires_minutes"}


def test_maintenance_requires_separate_secret(client, monkeypatch):
    from routers import maintenance
    monkeypatch.setattr(maintenance, "get_settings", lambda: cloud_settings(crawler_job_token="a" * 40))
    crawler = MagicMock(side_effect=AssertionError("No crawl without maintenance authorization"))
    monkeypatch.setattr(maintenance, "FciCrawler", crawler)
    assert client.post("/api/v1/maintenance/update").status_code == 401
    assert client.post("/api/v1/maintenance/update", headers={"Authorization": "Bearer wrong"}).status_code == 401
    crawler.assert_not_called()


def test_public_signup_cannot_claim_admin(db, monkeypatch):
    from services import auth_service
    monkeypatch.setattr(auth_service, "get_settings", lambda: cloud_settings(environment="production", crawler_admin_emails=["owner@example.com"]))
    with pytest.raises(HTTPException) as error:
        auth_service.AuthService(db).register(UserCreate(email="owner@example.com", password="password-123"))
    assert error.value.status_code == 403


def test_bounded_chunking_preserves_long_words():
    chunks = chunk_pages([(1, "x" * 9000)], max_chars=1800, overlap_words=30)
    assert len(chunks) == 5
    assert all(len(chunk.text) <= 1800 for chunk in chunks)
    assert "".join(chunk.text for chunk in chunks) == "x" * 9000


def test_neon_url_uses_psycopg_and_preserves_ssl():
    settings = cloud_settings(database_url="postgresql://user:password@host/db?sslmode=require")
    assert settings.database_url == "postgresql+psycopg://user:password@host/db?sslmode=require"


def test_database_headroom_guard():
    from database.storage import check_storage
    connection = MagicMock()
    connection.dialect.name = "postgresql"
    connection.scalar.return_value = 800 * 1024 * 1024
    with pytest.raises(HTTPException) as error:
        check_storage(connection, 800)
    assert error.value.status_code == 507
    assert "pg_advisory_xact_lock" in str(connection.execute.call_args.args[0])
    connection.scalar.return_value = 100 * 1024 * 1024
    check_storage(connection, 800)


def test_upload_deletion_preserves_chat_and_other_accounts(db, users, monkeypatch):
    from models.circular import UploadSession
    from models.conversation import Conversation, Message
    from services.upload_service import UploadService
    from services import upload_service
    from rag.postgres_store import PostgresVectorStore
    settings = cloud_settings()
    monkeypatch.setattr(upload_service, "get_vector_store", lambda session: PostgresVectorStore(session))
    first, second = users
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    sessions = [UploadSession(user_id=user.id, filename="private.pdf", collection_name=f"upload_{index}", expires_at=expiry) for index, user in enumerate(users)]
    db.add_all(sessions)
    db.commit()
    store = PostgresVectorStore(db)
    for session in sessions:
        store.upsert_temp_chunks(session.collection_name, session.filename, [TextChunk("Private text", 1, 2)], [[1.0] * 768], expiry)
    chat = Conversation(user_id=first.id, title="Saved PDF conversation", source_mode="upload", upload_session_id=sessions[0].id)
    db.add(chat)
    db.flush()
    db.add(Message(conversation_id=chat.id, role="user", content="Keep my history"))
    db.commit()
    service = UploadService(db)
    with pytest.raises(HTTPException):
        service.delete_session(sessions[0].id, second)
    first_id = sessions[0].id
    service.delete_session(first_id, first)
    service.delete_session(first_id, first)
    assert db.get(UploadSession, first_id) is None
    assert store.count("upload_0") == 0
    assert store.count("upload_1") == 1
    assert db.get(Conversation, chat.id) is not None
    assert db.scalar(select(Message)).content == "Keep my history"
    sessions[1].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert service.cleanup_expired() == 1
    assert store.count("upload_1") == 0


def test_cleanup_authorization_and_no_crawler(client, monkeypatch):
    from routers import maintenance
    monkeypatch.setattr(maintenance, "get_settings", lambda: cloud_settings(crawler_job_token="a" * 40))
    service = MagicMock()
    service.cleanup_expired.return_value = 2
    monkeypatch.setattr(maintenance, "UploadService", lambda _: service)
    assert client.post("/api/v1/maintenance/cleanup").status_code == 401
    service.cleanup_expired.assert_not_called()
    result = client.post("/api/v1/maintenance/cleanup", headers={"Authorization": "Bearer " + "a" * 40})
    assert result.status_code == 200
    assert result.json() == {"deleted_uploads": 2}
