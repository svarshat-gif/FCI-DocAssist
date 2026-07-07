from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.circular import CircularChunk
from models.schemas import Citation, SummaryRequest, SummaryResponse
from rag.prompts import summary_prompt
from services.circular_service import CircularService
from services.gemini_service import GeminiService
from utils.text import snippet


class SummarizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.circulars = CircularService(db)
        self.gemini = GeminiService()

    def summarize(self, payload: SummaryRequest) -> SummaryResponse:
        circular = self.circulars.get_by_id_or_number(
            payload.circular_id,
            payload.circular_number,
        )
        if not circular:
            raise HTTPException(status_code=404, detail="Circular not found.")

        chunks = list(
            self.db.scalars(
                select(CircularChunk)
                .where(CircularChunk.circular_id == circular.id)
                .order_by(CircularChunk.chunk_index)
            ).all()
        )
        if not chunks:
            raise HTTPException(status_code=404, detail="Circular text not indexed.")

        source_text = "\n\n".join(
            f"[SRC-1] Page {chunk.page_number or 'Unknown'}: {chunk.text}"
            for chunk in chunks
        )
        # Gemini 2.5 Flash has a large context window, but keep this bounded for latency.
        source_text = source_text[:80000]
        data = self.gemini.generate_json(
            summary_prompt(payload.language, payload.style, source_text)
        )
        summary = str(data.get("answer_markdown") or "").strip()
        if not data.get("found") or not summary:
            summary = "I could not find this information in the indexed FCI Circulars."

        citation = Citation(
            source_id="SRC-1",
            circular_number=circular.circular_number,
            title=circular.title,
            publication_date=circular.publication_date,
            official_url=circular.official_url,
            page_number=None,
            snippet=snippet(chunks[0].text),
        )
        return SummaryResponse(summary=summary, citations=[citation])
