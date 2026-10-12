from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FCI Doc Assist"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/fci_docassist"
    )
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_output_tokens: int = Field(default=4096, ge=256, le=8192)
    llm_provider: Literal["gemini", "ollama"] = "gemini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    llm_timeout_seconds: int = 180
    embedding_model: str = "BAAI/bge-m3"
    embedding_provider: Literal["local", "gemini"] = "local"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_batch_size: int = Field(default=8, ge=1, le=32)
    vector_store: Literal["chroma", "postgres"] = "chroma"
    max_stored_chunks: int = Field(default=20000, ge=100, le=100000)
    database_storage_limit_mb: int = Field(default=800, ge=100, le=900)
    retrieval_max_distance: float = Field(default=0.65, ge=0, le=2)

    chroma_path: str = "./.chroma"
    chroma_collection: str = "fci_circulars"
    temp_upload_ttl_minutes: int = Field(default=60, ge=1, le=60)
    max_upload_mb: int = 25
    max_pdf_pages: int = Field(default=100, ge=1, le=1000)
    max_document_chunks: int = Field(default=300, ge=1, le=5000)

    fci_circular_urls: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["https://fci.gov.in/circular"])
    fci_request_timeout: int = 30
    crawler_max_pages: int = Field(default=40, ge=1, le=500)
    crawler_max_depth: int = Field(default=3, ge=0, le=6)
    crawler_max_documents_per_run: int = Field(default=5, ge=1, le=1000)
    crawler_job_token: str | None = None
    scheduler_enabled: bool = True
    crawl_on_start: bool = True
    crawler_admin_emails: Annotated[list[str], NoDecode] = Field(default_factory=list)
    crawler_daily_cron_hour: int = 2

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000"])

    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[2] / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://"):]
        return value

    @field_validator("fci_circular_urls", "cors_origins", "crawler_admin_emails", mode="before")
    @classmethod
    def parse_csv_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
