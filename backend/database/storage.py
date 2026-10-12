from fastapi import HTTPException
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from utils.config import get_settings


def check_storage(connection, limit_mb: int) -> None:
    if connection.dialect.name != "postgresql":
        return
    # Serialize app writes; leave generous room for indexes, WAL and maintenance.
    connection.execute(text("SELECT pg_advisory_xact_lock(62010412)"))
    used = connection.scalar(text("SELECT pg_database_size(current_database())"))
    if used >= limit_mb * 1024 * 1024:
        raise HTTPException(
            status_code=507,
            detail="Storage is nearly full. New data is paused; saved chats remain available. Please contact the administrator.",
        )


@event.listens_for(Session, "before_flush")
def guard_app_writes(session, _context, _instances):
    if session.new or any(session.is_modified(item, include_collections=False) for item in session.dirty):
        check_storage(session.connection(), get_settings().database_storage_limit_mb)
