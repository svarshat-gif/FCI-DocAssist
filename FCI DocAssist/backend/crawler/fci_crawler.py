from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from embeddings.embedder import get_embedder
from models.circular import Circular, CircularChunk
from rag.vector_store import ChromaVectorStore
from utils.config import get_settings
from utils.pdf import extract_pdf_text
from utils.text import (
    chunk_pages,
    clean_text,
    infer_circular_number,
    infer_topic,
    normalize_title,
    parse_date,
)

logger = logging.getLogger(__name__)


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
        self.vector_store = ChromaVectorStore()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "FCI-AI-Circular-Assistant/1.0 "
                    "(official circular indexing; contact local administrator)"
                )
            }
        )

    def run(self) -> CrawlerResult:
        result = CrawlerResult()
        discovered = self.discover()
        result.discovered = len(discovered)
        for item in discovered:
            try:
                status = self.index(item)
            except Exception as exc:  # noqa: BLE001 - crawler must continue.
                logger.exception("Failed to index %s", item.url)
                result.errors.append(f"{item.url}: {exc}")
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

        for root in roots:
            queue: list[tuple[str, int]] = [(root, 0)]
            root_host = urlparse(root).netloc
            while queue:
                page_url, depth = queue.pop(0)
                if page_url in visited_pages or depth > 1:
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

                    if depth < 1 and _looks_like_circular(candidate_text):
                        queue.append((absolute, depth + 1))

        return list(found.values())

    def index(self, item: DiscoveredCircular) -> str:
        if self.db.scalar(select(Circular).where(Circular.official_url == item.url)):
            return "skipped"

        pdf_bytes = self._fetch_bytes(item.url)
        if not pdf_bytes:
            return "skipped"
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        if self.db.scalar(select(Circular).where(Circular.file_hash == file_hash)):
            return "skipped"

        extracted = extract_pdf_text(pdf_bytes)
        chunks = chunk_pages(extracted.pages)
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
            response = self.session.get(
                url,
                timeout=self.settings.fci_request_timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Could not fetch %s: %s", url, exc)
            return None
        return response.text

    def _fetch_bytes(self, url: str) -> bytes | None:
        try:
            response = self.session.get(
                url,
                timeout=self.settings.fci_request_timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Could not download %s: %s", url, exc)
            return None
        content = response.content
        if not content.startswith(b"%PDF"):
            logger.warning("Skipping non-PDF response from %s", url)
            return None
        return content


def _same_site(root_host: str, url: str) -> bool:
    host = urlparse(url).netloc
    return not host or host == root_host


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
