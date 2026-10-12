import json
from unittest.mock import MagicMock, Mock

import httpx
import pytest
from fastapi import HTTPException
from google.genai.errors import APIError

from crawler.fci_public_api import FciPublicApi, official_url, record_documents
from services import gemini_service
from utils.config import Settings


def api():
    client = FciPublicApi(Mock(), Mock())
    client.key = b"1" * 32
    client.iv = b"2" * 16
    client.hash_key = b"public-test-value"
    return client


def test_public_transport_round_trip():
    client = api()
    data = {"result": {"data": []}, "status": 1}
    payload = client.encode(data)
    assert client.decode(payload["REQUEST_DATA"]) == data
    assert len(payload["REQUEST_TOKEN"]) == 64


def test_listing_pagination_and_future_date_filter():
    client = api()
    source = 'apiHashingKey:"public-test-value",this.data_secretKey="' + client.key.hex() + '",this.data_ivString="' + client.iv.decode() + '"'
    client.fetch_text.side_effect = ['<script src="main.test.js"></script>', source]
    pages = []
    for number in (1, 2):
        response = Mock(is_redirect=False)
        body = {"status": 1, "result": {"data": [{"intId": number}], "last_page": 2}}
        response.json.return_value = {"RESPONSE_DATA": client.encode(body)["REQUEST_DATA"]}
        pages.append(response)
    client.session.post.side_effect = pages
    assert list(client.records(5)) == [{"intId": 1}, {"intId": 2}]
    calls = client.session.post.call_args_list
    assert [call.kwargs["params"]["page"] for call in calls] == [1, 2]
    assert calls[0].kwargs["allow_redirects"] is False
    query = client.decode(calls[0].kwargs["json"]["REQUEST_DATA"])
    assert query["query"][0]["columnName"] == "VCHPUBLISH_DATE"


def test_official_pdf_links_in_descriptions_and_uploads():
    record = {"VCHU_DOCPLOAD": "file.pdf", "VCHTITLE": "Policy", "VCHPUBLISH_DATE": "2026-10-09", "jsonOptTxtDetails": '{"INTCIRCULARDIV":"Finance"}', "VCHDESC": '&lt;a href="https://fci.gov.in/admin/storage/ckeditor/new.pdf"&gt;PDF&lt;/a&gt;<a href="https://evil.example/x.pdf">external</a>'}
    documents = record_documents(record)
    assert len(documents) == 2
    assert documents[0]["department"] == "Finance"
    assert documents[1]["url"].endswith("/new.pdf")
    assert not official_url("https://fci.gov.in:invalid/x.pdf")
    assert not official_url("https://user:password@fci.gov.in/x.pdf")


@pytest.fixture
def gemini(monkeypatch):
    monkeypatch.setattr(gemini_service, "get_settings", lambda: Settings(_env_file=None, gemini_api_key="test-only-key"))
    factory = MagicMock()
    client = factory.return_value.__enter__.return_value
    monkeypatch.setattr(gemini_service.genai, "Client", factory)
    return gemini_service.GeminiService(), factory, client


def test_gemini_schema_timeouts_and_no_retry(gemini):
    service, factory, client = gemini
    expected = {"found": True, "answer_markdown": "Policy [SRC-1]", "used_source_ids": ["SRC-1"]}
    client.models.generate_content.return_value.text = json.dumps(expected)
    assert service.generate_json("Question") == expected
    options = factory.call_args.kwargs["http_options"]
    assert options.timeout == 180000 and options.retry_options.attempts == 1
    config = client.models.generate_content.call_args.kwargs["config"]
    assert config.response_schema is gemini_service.GroundedResponse
    assert config.thinking_config.thinking_budget == 0
    factory.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize("error,code", [(APIError(429, {"error": {"message": "Quota reached", "status": "RESOURCE_EXHAUSTED"}}), 429), (APIError(403, {"error": {"message": "Forbidden", "status": "PERMISSION_DENIED"}}), 503), (httpx.ReadTimeout("Timeout"), 503)])
def test_gemini_upstream_errors(gemini, error, code):
    service, _, client = gemini
    client.models.generate_content.side_effect = error
    with pytest.raises(HTTPException) as caught:
        service.generate_json("Question")
    assert caught.value.status_code == code
    assert client.models.generate_content.call_count == 1


def test_gemini_rejects_malformed_json(gemini):
    service, _, client = gemini
    client.models.generate_content.return_value.text = '{"found":"false"}'
    with pytest.raises(HTTPException) as caught:
        service.generate_json("Question")
    assert caught.value.status_code == 502


def test_gemini_missing_key(monkeypatch):
    monkeypatch.setattr(gemini_service, "get_settings", lambda: Settings(_env_file=None, gemini_api_key=None))
    with pytest.raises(HTTPException) as caught:
        gemini_service.GeminiService().generate_json("Question")
    assert caught.value.status_code == 503


def test_crawler_lock_releases_on_failure():
    from crawler.fci_crawler import FciCrawler, CrawlerBusyError, _crawl_lock
    crawler = object.__new__(FciCrawler)
    crawler.session = Mock()
    crawler._run = Mock(side_effect=ValueError("Test indexing error"))
    with pytest.raises(ValueError):
        crawler.run()
    assert not _crawl_lock.locked()
    crawler.session.close.assert_called_once()
    _crawl_lock.acquire()
    try:
        with pytest.raises(CrawlerBusyError):
            crawler.run()
    finally:
        _crawl_lock.release()


def test_allowlisted_administrator_can_start_crawl(client, users, monkeypatch):
    from routers import circulars
    from crawler.fci_crawler import CrawlerResult
    from utils.security import create_access_token
    monkeypatch.setattr(circulars, "get_settings", lambda: Settings(_env_file=None, crawler_admin_emails=[users[0].email]))
    factory = Mock()
    factory.return_value.run.return_value = CrawlerResult(discovered=1, indexed=1)
    monkeypatch.setattr(circulars, "FciCrawler", factory)
    response = client.post("/api/v1/circulars/crawl", headers={"Authorization": f"Bearer {create_access_token(users[0].id)}"})
    assert response.status_code == 200 and response.json()["indexed"] == 1
    from crawler.fci_crawler import CrawlerBusyError
    factory.return_value.run.side_effect = CrawlerBusyError("Already running")
    assert client.post("/api/v1/circulars/crawl", headers={"Authorization": f"Bearer {create_access_token(users[0].id)}"}).status_code == 409
