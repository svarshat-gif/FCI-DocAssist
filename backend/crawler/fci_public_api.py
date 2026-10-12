"""Read the same public circular listing used by FCI's website.

Transport constants are fetched from the public frontend, not stored credentials.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import re
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


def official_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        return parsed.scheme == "https" and (host == "fci.gov.in" or host.endswith(".fci.gov.in")) and parsed.port in {None, 443} and not parsed.username and not parsed.password
    except ValueError:
        return False


class FciPublicApi:
    def __init__(self, session: requests.Session, fetch_text, timeout: int = 30):
        self.session = session
        self.fetch_text = fetch_text
        self.timeout = timeout

    def records(self, max_pages: int):
        html = self.fetch_text("https://fci.gov.in/circular")
        if not html:
            raise ValueError("FCI circular listing could not be loaded.")
        soup = BeautifulSoup(html, "html.parser")
        script = next((tag.get("src") for tag in soup.find_all("script", src=True) if re.search(r"(?:^|/)main[.-].*\.js$", tag["src"])), None)
        script_url = urljoin("https://fci.gov.in/", script or "")
        if not script or not official_url(script_url):
            raise ValueError("FCI public frontend format changed; listing adapter needs an update.")
        source = self.fetch_text(script_url) or ""
        self.hash_key = self._constant(source, r'apiHashingKey:("[^"\n]+")').encode()
        self.key = bytes.fromhex(self._constant(source, r'this\.data_secretKey=("[^"\n]+")'))
        self.iv = self._constant(source, r'this\.data_ivString=("[^"\n]+")').encode()
        query = {
            "query": [
                {"columnName": "VCHPUBLISH_DATE", "operator": "<=", "value": date.today().isoformat(), "joinoperator": "and"},
                {"columnName": "VCHMEDIA_TYPE", "operator": "=", "value": 6, "joinoperator": "and"},
                {"columnName": "bitDeletedFlag", "operator": "=", "value": 0, "joinoperator": "and"},
                {"columnName": "tinPublishStatus", "operator": "=", "value": 1, "joinoperator": "and"},
            ],
            "orderBy": [{"columnName": "VCHPUBLISH_DATE", "type": "DESC"}],
        }
        payload = self.encode(query)
        for page in range(1, max_pages + 1):
            response = self.session.post(
                "https://fci.gov.in/admin/api/get-circular-list",
                params={"page": page, "limit": 100}, json=payload,
                timeout=self.timeout, allow_redirects=False,
            )
            response.raise_for_status()
            if response.is_redirect:
                raise ValueError("FCI listing unexpectedly redirected.")
            data = self.decode(response.json()["RESPONSE_DATA"])
            if data.get("status") != 1:
                raise ValueError("FCI public listing reported an error.")
            result = data["result"]
            rows = result["data"]
            yield from rows
            if not rows or page >= int(result["last_page"]):
                break

    @staticmethod
    def _constant(source: str, pattern: str) -> str:
        match = re.search(pattern, source)
        if not match:
            raise ValueError("FCI public transport format changed; listing adapter needs an update.")
        return json.loads(match[1])

    def encode(self, query: dict) -> dict:
        encoded = base64.b64encode(json.dumps(query, separators=(",", ":")).encode())
        padder = PKCS7(128).padder()
        padded = padder.update(encoded) + padder.finalize()
        encryptor = Cipher(algorithms.AES(self.key), modes.CBC(self.iv)).encryptor()
        return {
            "REQUEST_DATA": base64.b64encode(encryptor.update(padded) + encryptor.finalize()).decode(),
            "REQUEST_TOKEN": hmac.new(self.hash_key, encoded, hashlib.sha256).hexdigest(),
        }

    def decode(self, encrypted: str) -> dict:
        decryptor = Cipher(algorithms.AES(self.key), modes.CBC(self.iv)).decryptor()
        padded = decryptor.update(base64.b64decode(encrypted, validate=True)) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        decoded = unpadder.update(padded) + unpadder.finalize()
        return json.loads(base64.b64decode(decoded, validate=True))


def record_document(record: dict, url: str | None = None) -> dict | None:
    filename = record.get("VCHU_DOCPLOAD")
    if url is None:
        if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9_. -]+\.pdf", filename, flags=re.IGNORECASE):
            return None
        url = "https://fci.gov.in/fci-storage/storage/app/uploads/" + filename
    if not official_url(url) or not urlparse(url).path.lower().endswith(".pdf"):
        return None
    metadata = record.get("jsonOptTxtDetails") or "{}"
    try:
        metadata = json.loads(metadata) if isinstance(metadata, str) else metadata
    except ValueError:
        metadata = {}
    try:
        published = date.fromisoformat(record.get("VCHPUBLISH_DATE", "")[:10])
    except (ValueError, TypeError):
        published = None
    return {
        "url": url,
        "title": record.get("VCHTITLE") or filename or "FCI Circular",
        "publication_date": published,
        "department": metadata.get("INTCIRCULARDIV") if isinstance(metadata, dict) else None,
    }


def record_documents(record: dict) -> list[dict]:
    documents = {}
    uploaded = record_document(record)
    if uploaded:
        documents[uploaded["url"]] = uploaded
    urls = [record.get("VCHSOURCE_URL")]
    for field in ("VCHDESC", "VCH_DESC_HN"):
        soup = BeautifulSoup(html.unescape(record.get(field) or ""), "html.parser")
        urls.extend(tag["href"] for tag in soup.find_all("a", href=True))
    for url in urls:
        if isinstance(url, str) and url.strip():
            document = record_document(record, urljoin("https://fci.gov.in/", url.strip()))
            if document:
                documents[document["url"]] = document
    return list(documents.values())
