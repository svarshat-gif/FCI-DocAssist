from database.base import Base
from database.session import engine

# Import models so SQLAlchemy registers metadata before create_all.
from models.circular import Bookmark, Circular, CircularChunk, UploadSession  # noqa: F401
from models.conversation import Conversation, Message  # noqa: F401
from models.user import User  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
