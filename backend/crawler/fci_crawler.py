from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from threading import Lock
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from embeddings.embedder import get_embedder
from models.circular import Circular, CircularChunk
from rag.vector_store import get_vector_store
from utils.config import get_settings
from utils.pdf import extract_pdf_text
from crawler.fci_public_api import FciPublicApi, official_url, record_documents
from utils.text import (
    chunk_pages,
    clean_text,
    infer_circular_number,
    infer_topic,
    normalize_title,
    parse_date,
)

logger = logging.getLogger(__name__)
_crawl_lock = Lock()


class CrawlerBusyError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiscoveredCircular:
    url: str
    title: str
    publication_date: date | None = None
    department: str | None = None


@dataclass
class CrawlerResult:
    discovered: int = 0
    indexed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class FciCrawler:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.embedder = get_embedder()
        self._vector_store = None
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "FCI-AI-Circular-Assistant/1.0 "
                    "(official circular indexing; contact local administrator)"
                )
            }
        )

    @property
    def vector_store(self):
        if self._vector_store is None:
            self._vector_store = get_vector_store(self.db)
        return self._vector_store

    def run(self) -> CrawlerResult:
        if not _crawl_lock.acquire(blocking=False):
            raise CrawlerBusyError("A circular update is already running. Please try later.")
        try:
            return self._run()
        finally:
            self.session.close()
            _crawl_lock.release()

    def _run(self) -> CrawlerResult:
        result = CrawlerResult()
        discovered = self.discover()
        result.discovered = len(discovered)
        if not discovered:
            result.errors.append("No circular PDFs discovered. Configure the official circular index URL, including pagination URLs if necessary.")
        for item in discovered:
            if result.indexed >= self.settings.crawler_max_documents_per_run:
                break
            try:
                status = self.index(item)
            except Exception as exc:  # noqa: BLE001 - crawler must continue.
                self.db.rollback()
                logger.exception("Failed to index %s", item.url)
                result.errors.append(f"{item.url}: {exc}")
                if isinstance(exc, HTTPException) and exc.status_code in {429, 507}:
                    break
                continue
            if status == "indexed":
                result.indexed += 1
            else:
                result.skipped += 1
        return result

    def discover(self) -> list[DiscoveredCircular]:
        found: dict[str, DiscoveredCircular] = {}
        visited_pages: set[str] = set()
        roots = self.settings.fci_circular_urls or ["https://fci.gov.in/"]

        if any(_official_url(root) and not _is_pdf(root) for root in roots):
            try:
                api = FciPublicApi(self.session, self._fetch_text, self.settings.fci_request_timeout)
                for record in api.records(self.settings.crawler_max_pages):
                    for document in record_documents(record):
                        found[document["url"]] = DiscoveredCircular(**document)
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                logger.warning("FCI public API discovery failed; trying HTML links: %s", exc)

        for root in roots:
            if not _official_url(root):
                logger.warning("Ignoring non-FCI URL: %s", root)
                continue
            if _is_pdf(root):
                found[root] = DiscoveredCircular(url=root, title=normalize_title(urlparse(root).path.rsplit('/', 1)[-1]))
                continue
            queue: list[tuple[str, int]] = [(root, 0)]
            root_host = urlparse(root).netloc
            while queue and len(visited_pages) < self.settings.crawler_max_pages:
                page_url, depth = queue.pop(0)
                if page_url in visited_pages or depth > self.settings.crawler_max_depth:
                    continue
                visited_pages.add(page_url)
                html = self._fetch_text(page_url)
                if not html:
                    continue
                soup = BeautifulSoup(html, "html.parser")
                for anchor in soup.find_all("a"):
                    href = anchor.get("href")
                    if not href:
                        continue
                    absolute = urljoin(page_url, href)
                    if not _same_site(root_host, absolute):
                        continue
                    label = clean_text(anchor.get_text(" ", strip=True))
                    context = clean_text(anchor.parent.get_text(" ", strip=True))[:700]
                    candidate_text = f"{label} {href} {context}"

                    if _is_pdf(absolute):
                        if _looks_like_circular(candidate_text):
                            found[absolute] = DiscoveredCircular(
                                url=absolute,
                                title=normalize_title(label or context or absolute),
                                publication_date=_extract_date(candidate_text),
                                department=_extract_department(candidate_text),
                            )
                        continue

                    is_pagination = anchor.get("rel") == ["next"] or label.lower() in {"next", "older", "next page"} or label.isdigit()
                    if depth < self.settings.crawler_max_depth and (_looks_like_circular(candidate_text) or is_pagination):
                        queue.append((absolute, depth + 1))

        return list(found.values())

    def index(self, item: DiscoveredCircular) -> str:
        if not _official_url(item.url):
            raise ValueError("Only official FCI URLs can be indexed.")
        if self.db.scalar(select(Circular).where(Circular.official_url == item.url)):
            return "skipped"

        pdf_bytes = self._fetch_bytes(item.url)
        if not pdf_bytes:
            return "skipped"
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        if self.db.scalar(select(Circular).where(Circular.file_hash == file_hash)):
            return "skipped"

        extracted = extract_pdf_text(pdf_bytes, max_pages=self.settings.max_pdf_pages)
        if extracted.page_count > self.settings.max_pdf_pages:
            raise ValueError("Circular exceeds the configured page limit.")
        chunks = chunk_pages(extracted.pages, max_words=180, overlap_words=30, max_chars=1800) if self.settings.embedding_provider == "gemini" else chunk_pages(extracted.pages)
        if len(chunks) > self.settings.max_document_chunks:
            raise ValueError("Circular exceeds the configured document size limit.")
        if not chunks:
            raise ValueError("No extractable text found in circular PDF.")

        first_text = extracted.full_text[:4000]
        title = normalize_title(item.title)
        circular = Circular(
            circular_number=infer_circular_number(title, item.url, first_text),
            title=title,
            publication_date=item.publication_date or _extract_date(first_text),
            department=item.department or _extract_department(first_text),
            topic=infer_topic(f"{title} {first_text}"),
            official_url=item.url,
            file_hash=file_hash,
            page_count=extracted.page_count,
        )
        self.db.add(circular)
        self.db.flush()

        for index, chunk in enumerate(chunks):
            self.db.add(
                CircularChunk(
                    circular_id=circular.id,
                    chunk_index=index,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    token_count=chunk.token_count,
                )
            )
        embeddings = self.embedder.embed_documents([chunk.text for chunk in chunks])
        self.vector_store.upsert_circular_chunks(circular, chunks, embeddings)
        self.db.commit()
        logger.info("Indexed FCI circular %s", item.url)
        return "indexed"

    def _fetch_text(self, url: str) -> str | None:
        try:
            response = self._get(url)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Could not fetch %s: %s", url, exc)
            return None
        return response.text

    def _fetch_bytes(self, url: str) -> bytes | None:
        try:
            response = self._get(url)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Could not download %s: %s", url, exc)
            return None
        content = bytearray()
        for part in response.iter_content(chunk_size=65536):
            content.extend(part)
            if len(content) > self.settings.max_upload_bytes:
                response.close()
                raise ValueError("Circular PDF exceeds the configured download limit.")
        response.close()
        if not content.startswith(b"%PDF"):
            logger.warning("Skipping non-PDF response from %s", url)
            return None
        return bytes(content)

    def _get(self, url: str):
        for _ in range(6):
            if not _official_url(url):
                raise requests.RequestException("Refusing to leave the official FCI website.")
            response = self.session.get(url, timeout=self.settings.fci_request_timeout, allow_redirects=False, stream=True)
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            url = urljoin(url, response.headers.get("Location", ""))
            response.close()
        raise requests.RequestException("Too many redirects.")


def _same_site(root_host: str, url: str) -> bool:
    return _official_url(url)


def _official_url(url: str) -> bool:
    return official_url(url)


def _is_pdf(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def _looks_like_circular(value: str) -> bool:
    lowered = value.lower()
    keywords = (
        "circular",
        "office order",
        "notification",
        "policy",
        "establishment",
        "transfer",
        "promotion",
        "leave",
    )
    return any(keyword in lowered for keyword in keywords)


def _extract_date(value: str) -> date | None:
    patterns = [
        r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}",
        r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            parsed = parse_date(match.group(0))
            if parsed:
                return parsed
    return None


def _extract_department(value: str) -> str | None:
    lowered = value.lower()
    departments = {
        "Personnel": ("personnel", "establishment", "hr"),
        "Finance": ("finance", "accounts", "pension"),
        "Procurement": ("procurement", "purchase", "tender"),
        "Quality Control": ("quality", "qc", "inspection"),
        "Storage": ("storage", "depot", "godown"),
        "Vigilance": ("vigilance", "disciplinary"),
    }
    for department, keywords in departments.items():
        if any(keyword in lowered for keyword in keywords):
            return department
    return None
