"""Retrieval benchmark: which chunking, embedding, fusion and reranking choices find the cited pages.

Gold labels are eval/cases.yaml `expected_sources` (document file + page). A query "hits" a source when that
page is among the top-k distinct pages returned. Run inside the backend container, which has the app code,
the database with the ingested corpus and the cached models:

    docker compose cp eval/retrieval_bench.py backend:/tmp/retrieval_bench.py
    docker compose cp eval/cases.yaml backend:/tmp/cases.yaml
    docker compose exec -T backend python /tmp/retrieval_bench.py > eval/results/retrieval-bench.json

The production variant calls the real hybrid_search against Postgres; every other variant is in memory so
choices can be compared in minutes. The set is small (about 15 gold pages), so read differences of one
source as noise.
"""

import asyncio
import json
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml
from sqlalchemy import text

from app.db.session import get_sessionmaker
from app.ingest.chunk import chunk_pages
from app.ingest.parse import ParsedPage
from app.retrieval.hybrid import hybrid_search

CASES = Path("/tmp/cases.yaml")
KS = (3, 5)
STOP = set(
    "a an and are as at be by can do does for from has have how i if in is it its may must of on or the "
    "their there this to what when where which who whom whose why will with would my me you your we our".split()
)
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
NEGATIVES = [
    "How much does Northfield reimburse employees each month for home internet service?",
    "What is the university's policy on cryptocurrency mining on campus servers?",
    "What is the dress code for the IT help desk?",
    "How many vacation days do IT staff receive?",
    "What is the cafeteria menu this week?",
    "Which parking permit do students need for the library?",
    "What is the tuition for the data science master's program?",
    "Who won the 2026 football championship?",
]


def tokens(s: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", s.lower()):
        if w in STOP:
            continue
        for suf in ("ing", "ed", "es", "s"):  # light stemming so 'devices' matches 'device'
            if len(w) > len(suf) + 3 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.tf = [defaultdict(int) for _ in docs]
        self.len = []
        df: dict[str, int] = defaultdict(int)
        for i, d in enumerate(docs):
            toks = tokens(d)
            self.len.append(len(toks))
            for t in toks:
                self.tf[i][t] += 1
            for t in set(toks):
                df[t] += 1
        self.avg = sum(self.len) / max(len(docs), 1)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> np.ndarray:
        q = tokens(query)
        out = np.zeros(len(self.tf))
        for i, tf in enumerate(self.tf):
            norm = self.k1 * (1 - self.b + self.b * self.len[i] / self.avg)
            for t in q:
                if t in tf:
                    out[i] += self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + norm)
        return out


def rrf(rankings: list[list[int]], weights: list[float], k: int = 60) -> dict[int, float]:
    fused: dict[int, float] = defaultdict(float)
    for ranking, w in zip(rankings, weights, strict=True):
        for rank, idx in enumerate(ranking, start=1):
            fused[idx] += w / (k + rank)
    return fused


def pages_of(order: list[int], meta: list[tuple[str, int]], k: int) -> list[tuple[str, int]]:
    seen: list[tuple[str, int]] = []
    for idx in order:
        if meta[idx] not in seen:
            seen.append(meta[idx])
        if len(seen) == k:
            break
    return seen


def load_gold() -> tuple[list[dict], list[str]]:
    data = yaml.safe_load(CASES.read_text())
    gold, unanswerable = [], []
    for case in data["cases"]:
        query = " ".join(t["content"] for t in case["turns"])  # multi-turn cases: a standalone rewrite proxy
        sources = {(s["document_file"], s["page"]) for s in case.get("expected_sources", [])}
        if sources:
            gold.append({"id": case["id"], "category": case["category"], "query": query, "sources": sources})
        else:
            unanswerable.append(query)
    return gold, unanswerable


def score_variant(gold: list[dict], ranked: dict[str, list[tuple[str, int]]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k in KS:
        found = total = full = 0
        for case in gold:
            top = ranked[case["id"]][:k]
            hits = len(case["sources"] & set(top))
            found += hits
            total += len(case["sources"])
            full += hits == len(case["sources"])
        out[f"recall@{k}"] = round(found / total, 3)
        out[f"all_found@{k}"] = round(full / len(gold), 3)
    rr = []
    for case in gold:
        pos = [i for i, p in enumerate(ranked[case["id"]], start=1) if p in case["sources"]]
        rr.append(1 / pos[0] if pos else 0.0)
    out["mrr"] = round(sum(rr) / len(rr), 3)
    return out


async def load_pages() -> list[dict]:
    async with get_sessionmaker()() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT d.filename, d.title, p.page_number, p.text FROM document_pages p "
                    "JOIN documents d ON d.id = p.document_id WHERE d.source = 'corpus' "
                    "ORDER BY d.filename, p.page_number"
                )
            )
        ).all()
    return [{"file": r[0], "title": r[1], "page": r[2], "text": r[3]} for r in rows]


def build_chunks(pages: list[dict], size: int | None, overlap: int, context: bool) -> tuple[list[str], list[tuple[str, int]]]:
    texts, meta = [], []
    for doc_file in sorted({p["file"] for p in pages}):
        doc_pages = [p for p in pages if p["file"] == doc_file]
        title = doc_pages[0]["title"]
        if size is None:
            chunks = [(p["page"], None, p["text"]) for p in doc_pages]
        else:
            parsed = [ParsedPage(p["page"], p["text"]) for p in doc_pages]
            chunks = [(c.page_number, c.section, c.text) for c in chunk_pages(parsed, size, overlap)]
        for page, section, body in chunks:
            prefix = f"{title}" + (f" | {section}" if section else "") + "\n" if context else ""
            texts.append(prefix + body)
            meta.append((doc_file, page))
    return texts, meta


_EMB: dict[str, object] = {}


def embedder(model: str):
    from fastembed import TextEmbedding

    if model not in _EMB:
        _EMB[model] = TextEmbedding(model)
    return _EMB[model]


def embed(model: str, texts: list[str]) -> np.ndarray:
    vecs = np.array([v for v in embedder(model).embed(texts, batch_size=32)])
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def main_sync() -> None:
    gold, unanswerable = load_gold()
    pages = asyncio.run(load_pages())
    results: list[dict] = []
    probes = {"positive": [g["query"] for g in gold], "negative": unanswerable + NEGATIVES}

    async def production() -> dict[str, list[tuple[str, int]]]:
        ranked: dict[str, list[tuple[str, int]]] = {}
        async with get_sessionmaker()() as db:
            for case in gold:
                res = await hybrid_search(db, case["query"], None, top_k=12)
                files = {
                    str(r[0]): r[1]
                    for r in (await db.execute(text("SELECT id, filename FROM documents"))).all()
                }
                seen: list[tuple[str, int]] = []
                for h in res.hits:
                    key = (files[str(h.document_id)], h.page)
                    if key not in seen:
                        seen.append(key)
                ranked[case["id"]] = seen
        return ranked

    prod = asyncio.run(production())
    results.append({"variant": "PRODUCTION (current settings: Postgres FTS + vector RRF)", **score_variant(gold, prod)})
    if "--production-only" in sys.argv:  # quick check of the real pipeline after a settings change
        json.dump({"results": results, "gold_cases": len(gold)}, sys.stdout, indent=1)
        return

    from fastembed.rerank.cross_encoder import TextCrossEncoder

    rerankers = {name: TextCrossEncoder(name) for name in ("Xenova/ms-marco-MiniLM-L-6-v2", "Xenova/ms-marco-MiniLM-L-12-v2")}
    calibration: dict[str, dict] = {}
    chunkings = {"350/50": (350, 50), "200/30": (200, 30), "500/75": (500, 75), "whole-page": (None, 0)}
    models = {"small": "BAAI/bge-small-en-v1.5", "base": "BAAI/bge-base-en-v1.5"}

    for cname, (size, overlap) in chunkings.items():
        for context in (False, True):
            texts, meta = build_chunks(pages, size, overlap, context)
            bm = BM25(texts)
            for mname, model in models.items():
                started = time.time()
                mat = embed(model, texts)
                index_s = round(time.time() - started, 1)
                for qprefix in (False, True):
                    label = f"{cname} ctx={'y' if context else 'n'} {mname} qprefix={'y' if qprefix else 'n'}"
                    dense_rank: dict[str, list[int]] = {}
                    bm_rank: dict[str, list[int]] = {}
                    dense_scores: dict[str, np.ndarray] = {}
                    for case in gold:
                        q = (BGE_QUERY_PREFIX if qprefix else "") + case["query"]
                        qv = embed(model, [q])[0]
                        sims = mat @ qv
                        dense_scores[case["id"]] = sims
                        dense_rank[case["id"]] = list(np.argsort(-sims)[:20])
                        bm_rank[case["id"]] = list(np.argsort(-bm.scores(case["query"]))[:20])
                    modes = {
                        "dense": {c: pages_of(dense_rank[c], meta, 10) for c in dense_rank},
                        "bm25": {c: pages_of(bm_rank[c], meta, 10) for c in bm_rank},
                        "hybrid": {
                            c: pages_of(
                                sorted(
                                    (f := rrf([dense_rank[c], bm_rank[c]], [1.0, 1.0])), key=lambda i: -f[i]
                                ),
                                meta,
                                10,
                            )
                            for c in dense_rank
                        },
                        "hybrid 0.6d/0.4b": {
                            c: pages_of(
                                sorted((f := rrf([dense_rank[c], bm_rank[c]], [0.6, 0.4])), key=lambda i: -f[i]),
                                meta,
                                10,
                            )
                            for c in dense_rank
                        },
                    }
                    for mode, ranked in modes.items():
                        if mode == "bm25" and (mname, qprefix) != ("small", False):
                            continue  # BM25 does not depend on the embedding model or query prefix
                        results.append({"variant": f"{label} | {mode}", "index_s": index_s, **score_variant(gold, ranked)})
                    if qprefix is False and mname == "small" or (mname == "base" and qprefix):
                        for rname, rr in rerankers.items():
                            ranked = {}
                            for case in gold:
                                fused = rrf([dense_rank[case["id"]], bm_rank[case["id"]]], [1.0, 1.0])
                                cand = sorted(fused, key=lambda i: -fused[i])[:30]
                                sc = list(rr.rerank(case["query"], [texts[i] for i in cand]))
                                order = [cand[i] for i in np.argsort(-np.array(sc))]
                                ranked[case["id"]] = pages_of(order, meta, 10)
                            results.append(
                                {"variant": f"{label} | hybrid+rerank {rname.split('/')[-1]}", **score_variant(gold, ranked)}
                            )

    # Score distributions for answerable vs unanswerable questions: the basis for the "weak result" cutoff.
    texts, _ = build_chunks(pages, 350, 50, False)
    mats = {m: embed(model, texts) for m, model in models.items()}
    for mname, model in models.items():
        for qprefix in (False, True):
            def best(qs, mat=mats[mname], model=model, qprefix=qprefix):
                return [
                    round(float(np.max(mat @ embed(model, [(BGE_QUERY_PREFIX if qprefix else "") + q])[0])), 3)
                    for q in qs
                ]

            calibration[f"cosine {mname} qprefix={'y' if qprefix else 'n'}"] = {k: best(v) for k, v in probes.items()}
    for rname, rr in rerankers.items():
        def best_rerank(qs, rr=rr):
            out = []
            for q in qs:
                top = np.argsort(-(mats["small"] @ embed(models["small"], [q])[0]))[:10]
                out.append(round(float(max(rr.rerank(q, [texts[i] for i in top]))), 3))
            return out

        calibration[f"rerank {rname.split('/')[-1]}"] = {k: best_rerank(v) for k, v in probes.items()}
    json.dump({"results": results, "calibration": calibration, "gold_cases": len(gold)}, sys.stdout, indent=1)


if __name__ == "__main__":
    main_sync()
