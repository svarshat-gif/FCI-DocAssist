import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Circular(Base):
    __tablename__ = "circulars"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    circular_number: Mapped[str | None] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    publication_date: Mapped[date | None] = mapped_column(Date, index=True)
    department: Mapped[str | None] = mapped_column(String(180), index=True)
    topic: Mapped[str | None] = mapped_column(String(180), index=True)
    official_url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    source_type: Mapped[str] = mapped_column(String(40), default="official")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    chunks = relationship(
        "CircularChunk",
        back_populates="circular",
        cascade="all, delete-orphan",
    )
    bookmarks = relationship("Bookmark", back_populates="circular")


class CircularChunk(Base):
    __tablename__ = "circular_chunks"
    __table_args__ = (
        UniqueConstraint("circular_id", "chunk_index", name="uq_circular_chunk_index"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    circular_id: Mapped[str] = mapped_column(ForeignKey("circulars.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    circular = relationship("Circular", back_populates="chunks")


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    collection_name: Mapped[str] = mapped_column(String(120), unique=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    session_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    user = relationship("User", back_populates="upload_sessions")


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "circular_id", name="uq_user_bookmark"),)

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    circular_id: Mapped[str] = mapped_column(ForeignKey("circulars.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="bookmarks")
    circular = relationship("Circular", back_populates="bookmarks")
