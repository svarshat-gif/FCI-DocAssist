import json
import re
from typing import Any

from fastapi import HTTPException, status
from google import genai
from google.genai import types
from google.genai.errors import APIError
import httpx
import requests
from pydantic import BaseModel, ConfigDict, Field

from utils.config import get_settings
from rag.prompts import SYSTEM_GUARDRAIL


class GroundedResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    found: bool
    answer_markdown: str
    used_source_ids: list[str] = Field(description="Only IDs present in the supplied source excerpts.")


class GeminiService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate_json(self, prompt: str, temperature: float = 0.1) -> dict[str, Any]:
        if self.settings.llm_provider == "ollama":
            try:
                response = requests.post(
                    f"{self.settings.ollama_base_url.rstrip('/')}/api/generate",
                    json={"model": self.settings.ollama_model, "system": SYSTEM_GUARDRAIL, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": temperature}},
                    timeout=self.settings.llm_timeout_seconds,
                )
                response.raise_for_status()
                return parse_json_response(response.json().get("response", "{}"))
            except (requests.RequestException, ValueError) as exc:
                raise HTTPException(status_code=503, detail="The assistant is unavailable right now. Please contact the administrator.") from exc
        if not self.settings.gemini_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The assistant is not ready yet. Please contact the administrator.",
            )
        try:
            with genai.Client(
                api_key=self.settings.gemini_api_key,
                http_options=types.HttpOptions(
                    timeout=self.settings.llm_timeout_seconds * 1000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            ) as client:
                response = client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_GUARDRAIL,
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_schema=GroundedResponse,
                        max_output_tokens=self.settings.gemini_max_output_tokens,
                        thinking_config=types.ThinkingConfig(thinking_budget=0) if self.settings.gemini_model.startswith("gemini-2.5-flash") else None,
                    ),
                )
        except APIError as exc:
            if exc.code == 429:
                raise HTTPException(status_code=429, detail="The assistant has reached its current usage limit. Please try again later.", headers={"Retry-After": "60"}) from exc
            raise HTTPException(status_code=503, detail="The assistant is unavailable right now. Please try again later or contact the administrator.") from exc
        except (httpx.HTTPError, requests.RequestException) as exc:
            raise HTTPException(status_code=503, detail="The assistant could not be reached. Please try again later.") from exc
        try:
            return GroundedResponse.model_validate_json(response.text or "{}").model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="The answer could not be completed. Please try again.") from exc


def parse_json_response(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
