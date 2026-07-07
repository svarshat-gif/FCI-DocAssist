import re
from dataclasses import dataclass
from datetime import date, datetime


WHITESPACE_RE = re.compile(r"\s+")
DATE_PATTERNS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
)


@dataclass(frozen=True)
class TextChunk:
    text: str
    page_number: int | None
    token_count: int


def clean_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value.replace("\x00", " ")).strip()


def normalize_title(value: str) -> str:
    value = clean_text(value)
    return value[:500] if value else "Untitled FCI Circular"


def estimate_tokens(value: str) -> int:
    return max(1, len(value.split()))


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    cleaned = clean_text(value)
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(cleaned, pattern).date()
        except ValueError:
            continue
    match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", cleaned)
    if not match:
        return None
    day, month, year = match.groups()
    if len(year) == 2:
        year = f"20{year}"
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def infer_circular_number(*values: str | None) -> str | None:
    joined = " ".join(clean_text(value or "") for value in values)
    patterns = [
        r"(?:Circular|Cir\.?|Office\s+Order|Order|No\.?)\s*(?:No\.?)?\s*[:\-]?\s*([A-Za-z0-9./\-_]+)",
        r"\b([A-Z]{1,8}[-/]\d{1,4}[-/]\d{2,4})\b",
        r"\b(\d{1,4}/\d{4})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, joined, flags=re.IGNORECASE)
        if match:
            return match.group(1)[:120]
    return None


def infer_topic(text: str) -> str | None:
    lowered = text.lower()
    topics = {
        "Transfer": ("transfer", "posting", "relocation"),
        "Promotion": ("promotion", "seniority", "dpc"),
        "Leave": ("leave", "maternity", "paternity", "earned leave"),
        "Recruitment": ("recruitment", "vacancy", "appointment"),
        "Finance": ("finance", "salary", "pay", "allowance", "pension"),
        "Disciplinary": ("disciplinary", "vigilance", "conduct"),
        "Procurement": ("procurement", "tender", "purchase"),
    }
    for topic, keywords in topics.items():
        if any(keyword in lowered for keyword in keywords):
            return topic
    return None


def chunk_pages(
    pages: list[tuple[int, str]],
    max_words: int = 420,
    overlap_words: int = 70,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page_number, page_text in pages:
        words = clean_text(page_text).split()
        if not words:
            continue
        start = 0
        while start < len(words):
            end = min(start + max_words, len(words))
            chunk_words = words[start:end]
            text = " ".join(chunk_words).strip()
            if text:
                chunks.append(
                    TextChunk(
                        text=text,
                        page_number=page_number,
                        token_count=estimate_tokens(text),
                    )
                )
            if end >= len(words):
                break
            start = max(0, end - overlap_words)
    return chunks


def snippet(value: str, length: int = 360) -> str:
    cleaned = clean_text(value)
    if len(cleaned) <= length:
        return cleaned
    return f"{cleaned[: length - 3].rstrip()}..."
