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


@dataclass(frozen=True)
class SearchResult:
    hits: list[Hit]
    weak: bool
    top_score: float | None
    off_topic: bool = False


def _or_query(query: str) -> str:
    terms = [w.lower() for w in _WORD.findall(query) if w.lower() not in _STOP]
    return " | ".join(dict.fromkeys(terms))


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
           1 - (c.embedding <=> CAST(:q AS vector)) AS cosine
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE {_VISIBLE}
    ORDER BY c.embedding <=> CAST(:q AS vector)
    LIMIT :n
    """
)

_TEXT_SQL = text(
    f"""
    SELECT c.id, c.document_id, d.title, c.page_number, c.section, c.text,
           ts_rank_cd(c.tsv, to_tsquery('english', :tsq)) AS rank
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE {_VISIBLE} AND c.tsv @@ to_tsquery('english', :tsq)
    ORDER BY rank DESC
    LIMIT :n
    """
)


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
    tsq = _or_query(query)
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
        )
        for cid in ordered
    ]
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
