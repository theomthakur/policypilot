from collections.abc import Callable
from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def make_pdf(tmp_path: Path) -> Callable[..., Path]:
    """Build a small text PDF: one string per page, with optional repeated header and footer."""

    def _make(
        pages: list[str], name: str = "doc.pdf", header: str | None = None, footer: str | None = None
    ) -> Path:
        doc = pymupdf.open()
        for i, body in enumerate(pages, start=1):
            page = doc.new_page()
            y = 50
            if header:
                page.insert_text((50, y), header)
                y += 20
            page.insert_textbox(pymupdf.Rect(50, y, 550, 760), body, fontsize=10)
            if footer:
                page.insert_text((50, 800), f"{footer} {i}")
        path = tmp_path / name
        doc.save(path)
        doc.close()
        return path

    return _make
