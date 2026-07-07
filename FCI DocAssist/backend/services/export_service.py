from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from services.chat_service import ChatService


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.chat = ChatService(db)

    def export_txt(self, conversation_id: str, user) -> bytes:
        messages = self.chat.messages(conversation_id, user)
        lines: list[str] = ["FCI AI Circular Assistant Conversation", ""]
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
        document = SimpleDocTemplate(buffer, pagesize=A4, title="FCI Conversation")
        styles = getSampleStyleSheet()
        story = [Paragraph("FCI AI Circular Assistant Conversation", styles["Title"])]
        story.append(Spacer(1, 16))
        for message in messages:
            story.append(Paragraph(message.role.upper(), styles["Heading3"]))
            story.append(Paragraph(_escape(message.content), styles["BodyText"]))
            if message.citations:
                story.append(Paragraph("Citations", styles["Heading4"]))
                for citation in message.citations:
                    line = (
                        f"{citation.get('title')} | {citation.get('official_url')} "
                        f"| page {citation.get('page_number') or 'n/a'}"
                    )
                    story.append(Paragraph(_escape(line), styles["BodyText"]))
            story.append(Spacer(1, 12))
        document.build(story)
        return buffer.getvalue()


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
