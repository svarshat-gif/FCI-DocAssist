from __future__ import annotations

import io
from dataclasses import dataclass

import fitz
import pdfplumber

from utils.text import clean_text


@dataclass(frozen=True)
class ExtractedPdf:
    pages: list[tuple[int, str]]
    page_count: int

    @property
    def full_text(self) -> str:
        return "\n\n".join(text for _, text in self.pages)


def extract_pdf_text(pdf_bytes: bytes) -> ExtractedPdf:
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Uploaded file is not a valid PDF.")

    pages: list[tuple[int, str]] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = clean_text(page.extract_text() or "")
            pages.append((index, text))

    if any(text for _, text in pages):
        return ExtractedPdf(pages=pages, page_count=len(pages))

    fallback_pages: list[tuple[int, str]] = []
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for index, page in enumerate(document, start=1):
            fallback_pages.append((index, clean_text(page.get_text("text") or "")))
    finally:
        document.close()
    return ExtractedPdf(pages=fallback_pages, page_count=len(fallback_pages))
