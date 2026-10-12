from fastapi import HTTPException
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.circular import CircularChunk
from models.schemas import Citation, SummaryRequest, SummaryResponse, SUPPORTED_LANGUAGES
from models.conversation import Conversation, Message
from models.user import User
from rag.prompts import summary_prompt
from services.circular_service import CircularService
from services.gemini_service import GeminiService
from utils.text import snippet


class SummarizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.circulars = CircularService(db)
        self.gemini = GeminiService()

    def summarize(self, payload: SummaryRequest, user: User) -> SummaryResponse:
        if payload.language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail="Unsupported language.")
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
            raise HTTPException(status_code=404, detail="This circular is not ready to read yet. Please try again later.")

        source_text = "\n\n".join(
            f"[SRC-1] Page {chunk.page_number or 'Unknown'}: {chunk.text}"
            for chunk in chunks
        )
        # Gemini 2.5 Flash has a large context window, but keep this bounded for latency.
        source_text = source_text[:80000]
        data = self.gemini.generate_json(
            summary_prompt(payload.language, payload.style, source_text)
        )
        raw_summary = data.get("answer_markdown")
        summary = raw_summary.strip() if isinstance(raw_summary, str) else ""
        supported = data.get("found") is True and bool(summary) and data.get("used_source_ids") == ["SRC-1"] and set(re.findall(r"\[(SRC-\d+)\]", summary)) == {"SRC-1"}
        if not supported:
            summary = "I could not find this information in the available FCI circulars."

        citation = Citation(
            source_id="SRC-1",
            circular_number=circular.circular_number,
            title=circular.title,
            publication_date=circular.publication_date,
            official_url=circular.official_url,
            page_number=None,
            snippet=snippet(chunks[0].text),
        )
        conversation = Conversation(user_id=user.id, title=f"Summary: {circular.title}"[:70], language=payload.language, source_mode="official")
        self.db.add(conversation)
        self.db.flush()
        citations = [citation] if supported else []
        self.db.add_all([
            Message(conversation_id=conversation.id, role="user", content=f"Create a {payload.style} summary of {circular.circular_number or circular.title}.", citations=[]),
            Message(conversation_id=conversation.id, role="assistant", content=summary, citations=[item.model_dump(mode="json") for item in citations]),
        ])
        self.db.commit()
        return SummaryResponse(conversation_id=conversation.id, summary=summary, citations=citations)
