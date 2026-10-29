from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from app.ingest.chunk import chunk_page, chunk_pages, count_tokens
from app.ingest.embed import FakeEmbedder
from app.ingest.parse import ParsedPage, UnsupportedPdfError, parse_pdf

POLICY = (
    "1. Guest Network\n\n"
    "Guests may use the guest Wi-Fi network. The guest network is limited to 10 Mbps download. "
    "Unregistered devices are removed after 24 hours.\n\n"
    "2. Prohibited Uses\n\n"
    "Users must not share credentials. Users must not run unauthorized servers."
)


def test_parse_keeps_one_entry_per_page_and_strips_repeated_headers(make_pdf: Callable[..., Path]) -> None:
    path = make_pdf(
        [POLICY, "Page two text about MFA.", "Page three text about VPN."],
        header="Northfield University Office of IT",
        footer="Page",
    )
    parsed = parse_pdf(path, max_pages=100)
    assert [p.number for p in parsed.pages] == [1, 2, 3]
    assert all("Northfield University Office of IT" not in p.text for p in parsed.pages)
    assert "10 Mbps" in parsed.pages[0].text


def test_parse_rejects_pdfs_without_text(make_pdf: Callable[..., Path]) -> None:
    with pytest.raises(UnsupportedPdfError, match="No text layer"):
        parse_pdf(make_pdf(["", ""]), max_pages=100)


def test_parse_rejects_too_many_pages(make_pdf: Callable[..., Path]) -> None:
    with pytest.raises(UnsupportedPdfError, match="limit"):
        parse_pdf(make_pdf(["a b c"] * 3), max_pages=2)


def test_parse_rejects_non_pdf(tmp_path: Path) -> None:
    bad = tmp_path / "x.pdf"
    bad.write_text("not a pdf")
    with pytest.raises(UnsupportedPdfError):
        parse_pdf(bad, max_pages=100)


def test_chunks_never_cross_pages_and_keep_sections() -> None:
    pages = [ParsedPage(1, POLICY), ParsedPage(2, "3. Remote Work\n\nUse the VPN. Encrypt your laptop.")]
    chunks = chunk_pages(pages, max_tokens=350, overlap_tokens=50)
    assert {c.page_number for c in chunks} == {1, 2}
    for c in chunks:
        flat = " ".join(pages[c.page_number - 1].text.split())
        assert c.text.split(". ")[0][:30] in flat  # chunk text comes from its own page
    assert chunks[0].section == "1. Guest Network"
    assert next(c for c in chunks if c.page_number == 2).section == "3. Remote Work"


def test_long_pages_split_with_overlap_and_respect_the_token_limit() -> None:
    sentence = "Encryption at rest is required for Level 3 data on every managed device."
    page = ParsedPage(1, " ".join([sentence] * 80))
    chunks = chunk_page(page, max_tokens=120, overlap_tokens=30)
    assert len(chunks) > 1
    assert all(c.token_count <= 120 for c in chunks)
    first_words = chunks[1].text.split(".")[0]
    assert first_words in chunks[0].text  # overlap carried forward
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_count_tokens_is_positive() -> None:
    assert count_tokens("hello world") > 0


def test_fake_embedder_is_deterministic_and_normalized() -> None:
    emb = FakeEmbedder(384)
    a, b, c = emb.embed(["guest wifi limit", "guest wifi limit", "password rotation"])
    assert a == b
    assert abs(sum(v * v for v in a) - 1.0) < 1e-6
    assert sum(x * y for x, y in zip(a, c, strict=True)) < sum(x * y for x, y in zip(a, b, strict=True))


def test_local_embedder_prefixes_queries_for_bge_but_not_passages() -> None:
    from app.ingest.embed import BGE_QUERY_INSTRUCTION, LocalEmbedder

    seen: list[str] = []

    class Stub:
        def embed(self, texts: list[str], batch_size: int = 32) -> list[Any]:
            seen.extend(texts)
            return [np.array([1.0, 0.0]) for _ in texts]

    embedder = LocalEmbedder.__new__(LocalEmbedder)
    embedder._model, embedder._name, embedder.dim = Stub(), "BAAI/bge-small-en-v1.5", 2
    embedder.embed(["a passage"])
    embedder.embed_query("a question")
    assert seen == ["a passage", BGE_QUERY_INSTRUCTION + "a question"]
    seen.clear()
    embedder._name = "sentence-transformers/all-MiniLM-L6-v2"
    embedder.embed_query("a question")
    assert seen == ["a question"]
