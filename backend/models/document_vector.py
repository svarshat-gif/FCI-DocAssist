import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class DocumentVector(Base):
    __tablename__ = "document_vectors"

    id: Mapped[str] = mapped_column(String(180), primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_name: Mapped[str] = mapped_column(String(120), index=True)
    embedding_model: Mapped[str] = mapped_column(String(150), index=True)
    text: Mapped[str] = mapped_column(Text)
    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
