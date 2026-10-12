from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


SUPPORTED_LANGUAGES = [
    "English",
    "Hindi",
    "Kannada",
    "Telugu",
    "Tamil",
    "Malayalam",
    "Marathi",
    "Gujarati",
    "Bengali",
    "Punjabi",
]


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class Citation(BaseModel):
    source_id: str
    circular_number: str | None = None
    title: str
    publication_date: date | None = None
    official_url: str
    page_number: int | None = None
    snippet: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str | None = None
    language: str = "English"
    source_mode: Literal["official", "upload"] = "official"
    upload_session_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[Citation]
    found: bool


class MessageRead(BaseModel):
    id: str
    role: str
    content: str
    citations: list[Citation] | list[dict] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(BaseModel):
    id: str
    title: str
    language: str
    source_mode: str
    upload_session_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CircularRead(BaseModel):
    id: str
    circular_number: str | None
    title: str
    publication_date: date | None
    department: str | None
    topic: str | None
    official_url: str
    page_count: int

    model_config = ConfigDict(from_attributes=True)


class CircularSearchResponse(BaseModel):
    items: list[CircularRead]
    total: int


class SummaryRequest(BaseModel):
    circular_id: str | None = None
    circular_number: str | None = None
    style: Literal["short", "detailed", "bullets"] = "short"
    language: str = "English"


class SummaryResponse(BaseModel):
    conversation_id: str
    summary: str
    citations: list[Citation]


class UploadSessionRead(BaseModel):
    id: str
    filename: str
    page_count: int
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CrawlerRunResponse(BaseModel):
    discovered: int
    indexed: int
    skipped: int
    errors: list[str]
