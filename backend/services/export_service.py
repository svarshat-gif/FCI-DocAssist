from io import BytesIO
from html import escape

import pymupdf
from sqlalchemy.orm import Session

from services.chat_service import ChatService


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.chat = ChatService(db)

    def export_txt(self, conversation_id: str, user) -> bytes:
        messages = self.chat.messages(conversation_id, user)
        lines: list[str] = ["FCI Doc Assist Conversation", ""]
        for message in messages:
            lines.append(f"{message.role.upper()}: {message.content}")
            if message.citations:
                lines.append("Citations:")
                for citation in message.citations:
                    lines.append(
                        f"- {citation.get('title')} | {citation.get('official_url')} "
                        f"| page {citation.get('page_number') or 'n/a'}"
                    )
            lines.append("")
        return "\n".join(lines).encode("utf-8")

    def export_pdf(self, conversation_id: str, user) -> bytes:
        messages = self.chat.messages(conversation_id, user)
        buffer = BytesIO()
        parts = ["<h1>FCI Doc Assist</h1>"]
        for message in messages:
            parts.append(f"<h2>{escape(message.role.title())}</h2><p>{_escape(message.content)}</p>")
            if message.citations:
                parts.append("<h3>Citations</h3>")
                for citation in message.citations:
                    line = (
                        f"{citation.get('circular_number') or 'Number unavailable'} | "
                        f"{citation.get('title')} | {citation.get('publication_date') or 'Date unavailable'} | {citation.get('official_url')} "
                        f"| page {citation.get('page_number') or 'n/a'}"
                    )
                    parts.append(f"<p class='source'>{_escape(line)}</p>")
        # Story provides HarfBuzz shaping and Noto fallback fonts for Indian scripts.
        story = pymupdf.Story("".join(parts), user_css="body {font-family: sans-serif; font-size: 11pt;} h1 {color: #1e7d32;} h2 {font-size: 12pt;} .source {font-size: 9pt; color: #444;}")
        writer = pymupdf.DocumentWriter(buffer)

        def rectfn(_rect_num, _filled):
            return pymupdf.Rect(0, 0, 595, 842), pymupdf.Rect(42, 42, 553, 800), None

        story.write(writer, rectfn)
        writer.close()
        return buffer.getvalue()


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
