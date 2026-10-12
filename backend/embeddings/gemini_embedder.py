import math

import httpx
from fastapi import HTTPException
from google import genai
from google.genai import types
from google.genai.errors import APIError

from utils.config import get_settings


class GeminiEmbedder:
    def __init__(self):
        self.settings = get_settings()

    def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        if not texts:
            return []
        if not self.settings.gemini_api_key:
            raise HTTPException(status_code=503, detail="The assistant is not ready yet. Please contact the administrator.")
        result = []
        try:
            with genai.Client(api_key=self.settings.gemini_api_key, http_options=types.HttpOptions(
                timeout=self.settings.llm_timeout_seconds * 1000, retry_options=types.HttpRetryOptions(attempts=1),
            )) as client:
                for offset in range(0, len(texts), self.settings.embedding_batch_size):
                    batch = texts[offset:offset + self.settings.embedding_batch_size]
                    response = client.models.embed_content(
                        model=self.settings.gemini_embedding_model, contents=batch,
                        config=types.EmbedContentConfig(task_type=task, output_dimensionality=768),
                    )
                    if not response.embeddings or len(response.embeddings) != len(batch):
                        raise ValueError("Missing document embeddings")
                    for embedding in response.embeddings:
                        values = embedding.values or []
                        if len(values) != 768 or not all(math.isfinite(value) for value in values):
                            raise ValueError("Invalid document embeddings")
                        magnitude = math.sqrt(sum(value * value for value in values))
                        if magnitude == 0:
                            raise ValueError("Empty document embedding")
                        result.append([value / magnitude for value in values])
        except APIError as exc:
            if exc.code == 429:
                raise HTTPException(status_code=429, detail="The assistant has reached its current usage limit. Please try again later.", headers={"Retry-After": "60"}) from exc
            raise HTTPException(status_code=503, detail="Document search is unavailable right now. Please try again later.") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Document search could not be reached. Please try again later.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="The document could not be prepared. Please try again.") from exc
        return result

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text[-1800:]], "RETRIEVAL_QUERY")[0]
