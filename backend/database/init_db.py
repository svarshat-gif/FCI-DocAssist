from database.base import Base
from database.session import engine

# Import models so SQLAlchemy registers metadata before create_all.
from models.circular import Bookmark, Circular, CircularChunk, UploadSession  # noqa: F401
from models.conversation import Conversation, Message  # noqa: F401
from models.user import User  # noqa: F401
from models.document_vector import DocumentVector  # noqa: F401
from sqlalchemy import text
from utils.config import get_settings


def init_db() -> None:
    if get_settings().vector_store == "postgres":
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    tables = [table for table in Base.metadata.sorted_tables if get_settings().vector_store == "postgres" or table.name != "document_vectors"]
    Base.metadata.create_all(bind=engine, tables=tables)
