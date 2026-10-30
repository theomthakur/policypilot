"""Hybrid retrieval: pgvector cosine + PostgreSQL full text, fused with Reciprocal Rank Fusion.

See docs/adr/0003. Results carry document and page so every hit is citable. A result set is `weak`
when it is empty or when neither the fused score nor the best vector similarity is convincing; the
agent uses that flag to decide whether to reformulate (REQ-C3).
"""

import asyncio
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ingest.embed import get_embedder

_WORD = re.compile(r"[A-Za-z0-9]{2,}")
_STOP = frozenset(
    {
        *("a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how"),
        *("i", "in", "is", "it", "my", "of", "on", "or", "our", "the", "to", "what", "when", "where"),
        *("which", "who", "why", "will", "with", "you", "your"),
    }
)


@dataclass(frozen=True)
class Hit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    title: str
    page: int
    section: str | None
    excerpt: str
    vector_rank: int | None
    text_rank: int | None
    fused_score: float
    cosine: float | None
    authority: str = "upload"
    effective_date: str | None = None
    version: str | None = None
    doc_family: str | None = None
    supersedes: tuple[str, ...] = ()  # documented statements, e.g. "states that it supersedes ..."
    related: bool = False  # added because it belongs to the same policy family as a top hit


@dataclass(frozen=True)
class SearchResult:
    hits: list[Hit]
    weak: bool
    top_score: float | None
    off_topic: bool = False


def _statements(raw: object) -> tuple[str, ...]:
    items = raw if isinstance(raw, list) else []
    return tuple(str(i.get("statement", "")) for i in items if isinstance(i, dict) and i.get("statement"))


def _terms(query: str) -> list[str]:
    return list(dict.fromkeys(w.lower() for w in _WORD.findall(query) if w.lower() not in _STOP))


_COMMON_SHARE = 0.4  # a term in more than this share of chunks says nothing about which chunk is relevant
_MIN_CHUNKS_FOR_COMMON = 100
_share_cache: dict[tuple[str, int], float] = {}


async def _without_common_terms(db: AsyncSession, terms: list[str]) -> list[str]:
    """Drop query words found in most institutional chunks (a page banner repeats the institution's name
    on every page, and an OR query rewards it). The share is measured over institutional chunks only,
    because the large reference documents dilute it. Keeps every term if all are common; does nothing
    on a tiny corpus."""
    total = int(
        (
            await db.execute(
                text(
                    "SELECT count(*) FROM chunks c JOIN documents d ON d.id = c.document_id "
                    "WHERE d.authority = 'institutional'"
                )
            )
        ).scalar_one()
    )
    if total < _MIN_CHUNKS_FOR_COMMON or not terms:
        return terms
    kept = []
    for term in terms:
        key = (term, total)
        if key not in _share_cache:
            found = (
                await db.execute(
                    text(
                        "SELECT count(*) FROM chunks c JOIN documents d ON d.id = c.document_id "
                        "WHERE d.authority = 'institutional' AND c.tsv @@ to_tsquery('english', :t)"
                    ),
                    {"t": term},
                )
            ).scalar_one()
            _share_cache[key] = int(found) / total
        if _share_cache[key] <= _COMMON_SHARE:
            kept.append(term)
    return kept or terms


def _or_query(terms: list[str]) -> str:
    return " | ".join(terms)


_VISIBLE = """
    d.status = 'ready'
    AND (d.session_id IS NULL OR d.session_id = :session_id)
    AND (:no_filter OR c.document_id = ANY(:document_ids))
    AND (CAST(:page_start AS int) IS NULL OR c.page_number >= :page_start)
    AND (CAST(:page_end AS int) IS NULL OR c.page_number <= :page_end)
"""

_VECTOR_SQL = text(
    f"""
    SELECT c.id, c.document_id, d.title, c.page_number, c.section, c.text,
           1 - (c.embedding <=> CAST(:q AS vector)) AS cosine,
           d.authority, d.effective_date, d.version, d.doc_family, d.supersedes
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE {_VISIBLE}
    ORDER BY c.embedding <=> CAST(:q AS vector)
    LIMIT :n
    """
)

_TEXT_SQL = text(
    f"""
    SELECT c.id, c.document_id, d.title, c.page_number, c.section, c.text,
           ts_rank_cd(c.tsv, to_tsquery('english', :tsq)) AS rank,
           d.authority, d.effective_date, d.version, d.doc_family, d.supersedes
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE {_VISIBLE} AND c.tsv @@ to_tsquery('english', :tsq)
    ORDER BY rank DESC
    LIMIT :n
    """
)


_SIBLING_SQL = text(
    """
    SELECT DISTINCT ON (c.document_id)
           c.id, c.document_id, d.title, c.page_number, c.section, c.text,
           1 - (c.embedding <=> CAST(:q AS vector)) AS cosine,
           d.authority, d.effective_date, d.version, d.doc_family, d.supersedes
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE d.status = 'ready' AND d.session_id IS NULL AND d.authority = 'institutional'
      AND d.doc_family = ANY(:families) AND c.document_id <> ALL(:have)
    ORDER BY c.document_id, c.embedding <=> CAST(:q AS vector)
    """
)


async def _family_siblings(
    db: AsyncSession, hits: list[Hit], vector: list[float], session_id: uuid.UUID | None
) -> list[Hit]:
    """Other versions in the same policy family as a top hit, so a newer or older rule is never missed
    just because the question's wording matched only one of them. Families come from verified metadata."""
    families = sorted({h.doc_family for h in hits[:3] if h.doc_family and h.authority == "institutional"})
    if not families:
        return []
    have = sorted({h.document_id for h in hits})
    rows = (await db.execute(_SIBLING_SQL, {"q": str(vector), "families": families, "have": have})).all()
    return [
        Hit(
            chunk_id=r[0],
            document_id=r[1],
            title=str(r[2]),
            page=int(r[3]),
            section=r[4],
            excerpt=str(r[5])[:1200],
            vector_rank=None,
            text_rank=None,
            fused_score=0.0,
            cosine=float(r[6]),
            authority=str(r[7]),
            effective_date=r[8],
            version=r[9],
            doc_family=r[10],
            supersedes=_statements(r[11]),
            related=True,
        )
        for r in rows
    ]


async def hybrid_search(
    db: AsyncSession,
    query: str,
    session_id: uuid.UUID | None,
    document_ids: list[uuid.UUID] | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    top_k: int | None = None,
) -> SearchResult:
    settings = get_settings()
    top_k = top_k or settings.search_top_k_default
    vector = await asyncio.to_thread(get_embedder().embed_query, query)
    params: dict[str, object] = {
        "session_id": session_id,
        "no_filter": not document_ids,
        "document_ids": document_ids or [],
        "page_start": page_start,
        "page_end": page_end,
        "n": settings.search_candidates,
    }
    vector_rows = (await db.execute(_VECTOR_SQL, {**params, "q": str(vector)})).all()
    tsq = _or_query(await _without_common_terms(db, _terms(query)))
    text_rows = (await db.execute(_TEXT_SQL, {**params, "tsq": tsq})).all() if tsq else []

    k = settings.rrf_k
    scores: dict[uuid.UUID, float] = {}
    rows: dict[uuid.UUID, tuple[object, ...]] = {}
    vrank: dict[uuid.UUID, int] = {}
    trank: dict[uuid.UUID, int] = {}
    cosine: dict[uuid.UUID, float] = {}
    for rank, row in enumerate(vector_rows, start=1):
        scores[row[0]] = scores.get(row[0], 0.0) + 1.0 / (k + rank)
        rows[row[0]], vrank[row[0]], cosine[row[0]] = row, rank, float(row[6])
    for rank, row in enumerate(text_rows, start=1):
        scores[row[0]] = scores.get(row[0], 0.0) + 1.0 / (k + rank)
        rows.setdefault(row[0], row)
        trank[row[0]] = rank

    if settings.reference_score_weight != 1.0:
        for cid, found in rows.items():
            if found[7] == "reference":
                scores[cid] *= settings.reference_score_weight
    ordered = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:top_k]
    hits = [
        Hit(
            chunk_id=cid,
            document_id=rows[cid][1],  # type: ignore[arg-type]
            title=str(rows[cid][2]),
            page=int(rows[cid][3]),  # type: ignore[call-overload]
            section=rows[cid][4],  # type: ignore[arg-type]
            excerpt=str(rows[cid][5])[:1200],
            vector_rank=vrank.get(cid),
            text_rank=trank.get(cid),
            fused_score=round(scores[cid], 5),
            cosine=cosine.get(cid),
            authority=str(rows[cid][7]),
            effective_date=rows[cid][8],  # type: ignore[arg-type]
            version=rows[cid][9],  # type: ignore[arg-type]
            doc_family=rows[cid][10],  # type: ignore[arg-type]
            supersedes=_statements(rows[cid][11]),
        )
        for cid in ordered
    ]
    if not document_ids:
        hits = hits + await _family_siblings(db, hits, vector, session_id)
    top_score = hits[0].fused_score if hits else None
    best_cosine = max((h.cosine for h in hits if h.cosine is not None), default=0.0)
    weak = not hits or (
        top_score is not None
        and top_score < settings.weak_score_threshold
        and best_cosine < settings.weak_min_cosine
    )
    off_topic = bool(
        settings.off_topic_check and not text_rows and best_cosine < settings.off_topic_max_cosine
    )
    return SearchResult(hits=hits, weak=weak, top_score=top_score, off_topic=off_topic)
