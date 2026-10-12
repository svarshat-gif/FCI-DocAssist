from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from models.circular import Bookmark, Circular, CircularChunk
from models.user import User


class CircularService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        query: str | None = None,
        circular_number: str | None = None,
        department: str | None = None,
        topic: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Circular], int]:
        stmt: Select[tuple[Circular]] = select(Circular)

        if circular_number:
            stmt = stmt.where(Circular.circular_number.ilike(f"%{circular_number}%"))
        if department:
            stmt = stmt.where(Circular.department.ilike(f"%{department}%"))
        if topic:
            stmt = stmt.where(Circular.topic.ilike(f"%{topic}%"))
        if start_date:
            stmt = stmt.where(Circular.publication_date >= start_date)
        if end_date:
            stmt = stmt.where(Circular.publication_date <= end_date)
        if query:
            like = f"%{query}%"
            matching_chunk_ids = select(CircularChunk.circular_id).where(
                CircularChunk.text.ilike(like)
            )
            stmt = stmt.where(
                or_(
                    Circular.title.ilike(like),
                    Circular.department.ilike(like),
                    Circular.topic.ilike(like),
                    Circular.circular_number.ilike(like),
                    Circular.id.in_(matching_chunk_ids),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0
        items = self.db.scalars(
            stmt.order_by(Circular.publication_date.desc().nullslast(), Circular.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return list(items), total

    def recent(self, limit: int = 8) -> list[Circular]:
        return list(
            self.db.scalars(
                select(Circular)
                .order_by(Circular.publication_date.desc().nullslast(), Circular.created_at.desc())
                .limit(limit)
            ).all()
        )

    def bookmarks(self, user: User) -> list[Circular]:
        return list(self.db.scalars(
            select(Circular).join(Bookmark, Bookmark.circular_id == Circular.id)
            .where(Bookmark.user_id == user.id).order_by(Bookmark.created_at.desc())
        ).all())

    def get_by_id_or_number(
        self,
        circular_id: str | None,
        circular_number: str | None,
    ) -> Circular | None:
        if circular_id:
            circular = self.db.get(Circular, circular_id)
            if circular:
                return circular
        if circular_number:
            return self.db.scalar(
                select(Circular).where(Circular.circular_number.ilike(f"%{circular_number}%"))
            )
        return None

    def add_bookmark(self, user: User, circular_id: str) -> Bookmark:
        circular = self.db.get(Circular, circular_id)
        if not circular:
            raise ValueError("Circular not found.")
        existing = self.db.scalar(
            select(Bookmark).where(
                Bookmark.user_id == user.id,
                Bookmark.circular_id == circular_id,
            )
        )
        if existing:
            return existing
        bookmark = Bookmark(user_id=user.id, circular_id=circular_id)
        self.db.add(bookmark)
        self.db.commit()
        self.db.refresh(bookmark)
        return bookmark

    def remove_bookmark(self, user: User, circular_id: str) -> None:
        bookmark = self.db.scalar(
            select(Bookmark).where(
                Bookmark.user_id == user.id,
                Bookmark.circular_id == circular_id,
            )
        )
        if bookmark:
            self.db.delete(bookmark)
            self.db.commit()
