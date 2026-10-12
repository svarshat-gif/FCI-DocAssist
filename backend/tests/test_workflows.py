import json
from datetime import datetime, timedelta, timezone

import pymupdf
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from models.circular import Circular, CircularChunk, UploadSession
from models.conversation import Conversation, Message
from models.schemas import ChatRequest
from rag.vector_store import ChromaVectorStore, RetrievedChunk
from services.chat_service import ChatService, NOT_FOUND
from services.upload_service import UploadService
from utils.config import Settings
from utils.security import create_access_token, get_password_hash, verify_password


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def source():
    return RetrievedChunk("old-id", "Transfers need written approval.", 0.1, "circular-1", "18/2024", "Transfer policy", None, "https://fci.gov.in/transfer.pdf", 2)


def test_csv_configuration(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,https://example.com")
    monkeypatch.setenv("FCI_CIRCULAR_URLS", "https://fci.gov.in/circulars")
    assert Settings(_env_file=None).cors_origins == ["http://localhost:3000", "https://example.com"]


def test_long_unicode_passwords_are_distinct():
    password = "\u0915" * 40
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password(password + "different", hashed)


def test_private_routes_require_login(client):
    for path in ["/chat/conversations", "/uploads/anything", "/circulars/bookmarks"]:
        assert client.get("/api/v1" + path).status_code == 401
    assert client.delete("/api/v1/chat/history").status_code == 401
    assert client.post("/api/v1/chat", json={"message": "Transfer policy?"}).status_code == 401


def test_conversation_isolation_and_clear_history(client, db, users):
    first, second = users
    first_chat = Conversation(user_id=first.id, title="Private first")
    second_chat = Conversation(user_id=second.id, title="Private second")
    db.add_all([first_chat, second_chat]); db.commit()
    response = client.get("/api/v1/chat/conversations", headers=headers(first))
    assert [item["id"] for item in response.json()] == [first_chat.id]
    assert client.get(f"/api/v1/chat/conversations/{first_chat.id}/messages", headers=headers(second)).status_code == 403
    assert client.get(f"/api/v1/chat/conversations/{first_chat.id}/export?format=txt", headers=headers(second)).status_code == 403
    assert client.delete("/api/v1/chat/history", headers=headers(first)).json() == {"deleted": 1}
    assert db.get(Conversation, second_chat.id) is not None
    db.add_all([Conversation(user_id=first.id, title=f"Chat {index}") for index in range(51)])
    db.commit()
    assert client.delete("/api/v1/chat/history", headers=headers(first)).json() == {"deleted": 51}


def test_upload_cannot_be_used_or_deleted_by_another_user(db, users, ai):
    first, second = users
    upload = UploadSession(user_id=first.id, filename="private.pdf", collection_name="private_pdf", expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
    db.add(upload); db.commit()
    with pytest.raises(HTTPException) as caught:
        ChatService(db)._collection_for_payload(ChatRequest(message="Question", source_mode="upload", upload_session_id=upload.id), second)
    assert caught.value.status_code == 403
    service = object.__new__(UploadService)
    service.db = db
    with pytest.raises(HTTPException) as caught:
        service.delete_session(upload.id, second)
    assert caught.value.status_code == 403


def test_uncited_or_invalid_model_answers_are_refused(db, users, ai):
    retriever, generator = ai
    retriever.retrieve.return_value = [source()]
    generator.generate_json.return_value = {"found": True, "answer_markdown": "Unsupported answer", "used_source_ids": ["SRC-999"]}
    result = ChatService(db).answer(ChatRequest(message="Transfer?"), users[0])
    assert result.answer == NOT_FOUND and not result.citations
    generator.generate_json.return_value = {"found": "false", "answer_markdown": "Unsupported answer", "used_source_ids": ["SRC-1"]}
    assert not ChatService(db).answer(ChatRequest(message="Transfer?"), users[0]).found
    generator.generate_json.return_value = {"found": True, "answer_markdown": "Unsupported answer [SRC-999]", "used_source_ids": ["SRC-1"]}
    assert not ChatService(db).answer(ChatRequest(message="Transfer?"), users[0]).found


def test_grounded_stream_and_followup_memory(client, db, users, ai):
    retriever, generator = ai
    retriever.retrieve.return_value = [source()]
    generator.generate_json.return_value = {"found": True, "answer_markdown": "Written approval is required. [SRC-1]", "used_source_ids": ["SRC-1"]}
    response = client.post("/api/v1/chat/stream", headers=headers(users[0]), json={"message": "What is the transfer policy?"})
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0]["type"] == "sources" and events[0]["citations"][0]["page_number"] == 2
    assert "".join(event["text"] for event in events if event["type"] == "delta") == events[-1]["response"]["answer"]
    conversation_id = events[-1]["response"]["conversation_id"]
    ChatService(db).answer(ChatRequest(message="Explain it simply.", conversation_id=conversation_id), users[0])
    assert "transfer policy" in retriever.retrieve.call_args.kwargs["question"]
    assert len(list(db.scalars(select(Message).where(Message.conversation_id == conversation_id)))) == 4


def test_summary_is_saved_and_can_be_exported(client, db, users, ai, monkeypatch):
    from services import summarization_service
    from services.export_service import ExportService
    circular = Circular(title="Transfer instructions", circular_number="18/2024", official_url="https://fci.gov.in/transfer.pdf", file_hash="a" * 64)
    db.add(circular); db.flush()
    db.add(CircularChunk(circular_id=circular.id, chunk_index=0, page_number=1, text="Written approval is required.")); db.commit()
    generator = ai[1]
    generator.generate_json.return_value = {"found": True, "answer_markdown": "Written approval is required. [SRC-1]", "used_source_ids": ["SRC-1"]}
    monkeypatch.setattr(summarization_service, "GeminiService", lambda: generator)
    response = client.post("/api/v1/circulars/summarize", headers=headers(users[0]), json={"circular_id": circular.id})
    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]
    exported = ExportService(db).export_pdf(conversation_id, users[0])
    with pymupdf.open(stream=exported, filetype="pdf") as document:
        assert "Written approval" in "".join(page.get_text() for page in document)
    assert b"Written approval" in ExportService(db).export_txt(conversation_id, users[0])


def test_bookmark_round_trip_and_crawl_authorization(client, db, users):
    circular = Circular(title="Leave", official_url="https://fci.gov.in/leave.pdf", file_hash="b" * 64)
    db.add(circular); db.commit()
    assert client.post(f"/api/v1/circulars/{circular.id}/bookmark", headers=headers(users[0])).status_code == 204
    assert len(client.get("/api/v1/circulars/bookmarks", headers=headers(users[0])).json()) == 1
    assert client.get("/api/v1/circulars/bookmarks", headers=headers(users[1])).json() == []
    assert client.delete(f"/api/v1/circulars/{circular.id}/bookmark", headers=headers(users[0])).status_code == 204
    assert client.get("/api/v1/circulars/bookmarks", headers=headers(users[0])).json() == []
    assert client.post("/api/v1/circulars/crawl", headers=headers(users[0])).status_code == 403


def test_empty_vector_store_does_not_query():
    from unittest.mock import Mock
    store = object.__new__(ChromaVectorStore)
    store.official_collection = Mock(return_value=Mock())
    store.official_collection.return_value.count.return_value = 0
    assert store.query([0.1, 0.2]) == []
    store.official_collection.return_value.query.assert_not_called()


def test_crawler_rejects_external_sources():
    from crawler.fci_crawler import _official_url
    assert _official_url("https://fci.gov.in/circular.pdf")
    assert not _official_url("https://fci.gov.in.attacker.example/circular.pdf")
    assert not _official_url("http://localhost/circular.pdf")


def test_history_search_pagination_and_private_metadata(client, db, users):
    first, second = users
    timestamp = datetime.now(timezone.utc)
    chats = [Conversation(user_id=first.id, title=f"Transfer question {index:02d}", updated_at=timestamp + timedelta(seconds=index)) for index in range(55)]
    literal = Conversation(user_id=first.id, title="100% allowance")
    hidden = Conversation(user_id=second.id, title="Transfer private")
    db.add_all([*chats, literal, hidden]); db.commit()
    first_page = client.get("/api/v1/chat/conversations?query=transfer&limit=50", headers=headers(first))
    older_page = client.get("/api/v1/chat/conversations?query=transfer&offset=50&limit=50", headers=headers(first))
    assert len(first_page.json()) == 50 and len(older_page.json()) == 5
    assert first_page.json()[0]["id"] == chats[-1].id
    assert len({item["id"] for item in first_page.json() + older_page.json()}) == 55
    literal_result = client.get("/api/v1/chat/conversations", params={"query": "%"}, headers=headers(first)).json()
    assert [item["id"] for item in literal_result] == [literal.id]
    own = client.get(f"/api/v1/chat/conversations/{chats[0].id}", headers=headers(first))
    assert own.json()["source_mode"] == "official"
    assert client.get(f"/api/v1/chat/conversations/{chats[0].id}", headers=headers(second)).status_code == 403
    assert client.get("/api/v1/chat/conversations/missing", headers=headers(first)).status_code == 404
    assert client.get("/api/v1/chat/conversations?limit=1000", headers=headers(first)).status_code == 422


def test_history_does_not_need_ai_or_document_engine(db, users, monkeypatch):
    from services import chat_service
    from unittest.mock import Mock
    retriever = Mock(side_effect=AssertionError("History must not start the document engine"))
    generator = Mock(side_effect=AssertionError("History must not start AI"))
    monkeypatch.setattr(chat_service, "Retriever", retriever)
    monkeypatch.setattr(chat_service, "GeminiService", generator)
    saved = Conversation(user_id=users[0].id, title="Saved conversation")
    db.add(saved); db.commit()
    service = ChatService(db)
    assert service.list_conversations(users[0])[0].id == saved.id
    assert service.get_conversation(saved.id, users[0]).title == saved.title
    assert service.messages(saved.id, users[0]) == []
    assert service.clear_history(users[0]) == 1
    retriever.assert_not_called()
    generator.assert_not_called()
