"""Page-bounded, sentence-aware chunking (docs/adr/0005). A chunk never crosses a page."""

import re
from dataclasses import dataclass
from functools import lru_cache

import tiktoken

from app.ingest.parse import ParsedPage

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_HEADING = re.compile(r"^(\d+(\.\d+)*\.?\s+\S.{0,100}|[A-Z][A-Za-z0-9 ,&/()'-]{2,80})$")


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    chunk_index: int
    section: str | None
    text: str
    token_count: int


@lru_cache
def _encoder() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder().encode(text))


def _is_heading(line: str) -> bool:
    line = line.strip()
    return bool(line) and not line.endswith((".", ",", ";", ":")) and bool(_HEADING.match(line))


def _units(page_text: str) -> list[tuple[str, str | None]]:
    """Split a page into sentences, remembering the most recent heading for each."""
    units: list[tuple[str, str | None]] = []
    section: str | None = None
    for block in page_text.split("\n\n"):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if _is_heading(lines[0]):
            section = lines[0]
            lines = lines[1:]
            if not lines:
                continue
        for sentence in _SENTENCE_SPLIT.split(" ".join(lines)):
            if sentence.strip():
                units.append((sentence.strip(), section))
    return units


def chunk_page(page: ParsedPage, max_tokens: int, overlap_tokens: int) -> list[TextChunk]:
    units = _units(page.text)
    chunks: list[TextChunk] = []
    current: list[str] = []
    current_tokens = 0
    section: str | None = None

    def flush() -> None:
        if current:
            text = " ".join(current)
            chunks.append(TextChunk(page.number, len(chunks), section, text, count_tokens(text)))

    for sentence, sentence_section in units:
        tokens = count_tokens(sentence)
        if current and current_tokens + tokens > max_tokens:
            flush()
            # Carry the tail of the previous chunk forward as overlap.
            carried: list[str] = []
            carried_tokens = 0
            for prev in reversed(current):
                t = count_tokens(prev)
                if carried_tokens + t > overlap_tokens:
                    break
                carried.insert(0, prev)
                carried_tokens += t
            current, current_tokens = carried, carried_tokens
        if not current:
            section = sentence_section
        current.append(sentence)
        current_tokens += tokens
    flush()
    return chunks


def chunk_pages(pages: list[ParsedPage], max_tokens: int, overlap_tokens: int) -> list[TextChunk]:
    return [c for page in pages for c in chunk_page(page, max_tokens, overlap_tokens)]
