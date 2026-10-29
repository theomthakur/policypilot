"""PDF parsing: one text string per page, cleaned. See docs/adr/0005."""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pymupdf

MIN_TEXT_CHARS_PER_DOC = 50


class UnsupportedPdfError(ValueError):
    """The file isn't a readable, text-based PDF."""


@dataclass(frozen=True)
class ParsedPage:
    number: int  # 1-based PDF page number
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    title: str
    pages: list[ParsedPage]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # join words hyphenated across lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _strip_repeated_edges(pages: list[list[str]]) -> list[list[str]]:
    """Remove header and footer lines that repeat on most pages (page numbers normalized)."""
    if len(pages) < 3:
        return pages

    def key(line: str) -> str:
        return re.sub(r"\d+", "#", line.strip().lower())

    edges: Counter[str] = Counter()
    for lines in pages:
        for line in {*lines[:2], *lines[-2:]}:
            if line.strip():
                edges[key(line)] += 1
    repeated = {k for k, n in edges.items() if n >= max(3, int(len(pages) * 0.6))}
    return [[ln for ln in lines if key(ln) not in repeated] for lines in pages]


def parse_pdf(path: Path, max_pages: int) -> ParsedDocument:
    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        raise UnsupportedPdfError("The file could not be opened as a PDF.") from exc
    with doc:
        if doc.needs_pass:
            raise UnsupportedPdfError("Password-protected PDFs aren't supported.")
        if doc.page_count == 0:
            raise UnsupportedPdfError("The PDF has no pages.")
        if doc.page_count > max_pages:
            raise UnsupportedPdfError(f"The PDF has {doc.page_count} pages; the limit is {max_pages}.")
        raw_lines = [page.get_text("text").splitlines() for page in doc]
        meta_title = (doc.metadata or {}).get("title") or ""

    cleaned = _strip_repeated_edges(raw_lines)
    pages = [ParsedPage(number=i + 1, text=_normalize("\n".join(lines))) for i, lines in enumerate(cleaned)]
    if sum(len(p.text) for p in pages) < MIN_TEXT_CHARS_PER_DOC:
        raise UnsupportedPdfError("No text layer found. Scanned PDFs need OCR, which isn't supported.")

    title = meta_title.strip() or _first_heading(pages) or path.stem
    return ParsedDocument(title=title[:300], pages=pages)


def _first_heading(pages: list[ParsedPage]) -> str | None:
    for line in pages[0].text.splitlines():
        if 3 <= len(line.strip()) <= 120:
            return line.strip()
    return None
