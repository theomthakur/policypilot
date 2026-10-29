"""Offline extractive model for running the whole stack without an API key.

It is not a language model: it plans, searches the real corpus, and quotes the best matching passage.
Retrieval, tool limits, citation verification and the trace are the real ones. Answers are extractive and
are labelled as such (model name `offline-extractive`); use a real model for answer quality.
"""

import json
import re
import uuid
from typing import Any

from app.llm.client import ModelResponse, ToolCall

_STOP = {
    "what",
    "which",
    "who",
    "when",
    "where",
    "how",
    "does",
    "the",
    "and",
    "for",
    "are",
    "is",
    "a",
    "of",
    "to",
}


def _call(name: str, args: dict[str, Any]) -> ToolCall:
    return ToolCall(f"call_{uuid.uuid4().hex[:8]}", name, args)


def _question(messages: list[dict[str, Any]]) -> str:
    text = next((m["content"] for m in messages if m["role"] == "user"), "")
    match = re.search(r"Question: (.+)", text) or re.search(r"originally asked: (.+)", text)
    return (match.group(1) if match else text).strip()


def _last_hits(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hits of the latest search; a weak result counts as no evidence."""
    for message in reversed(messages):
        if message["role"] == "tool" and '"hits"' in message["content"]:
            body = message["content"][message["content"].index("{") :]
            data = json.loads(body).get("data", {})
            return [] if data.get("weak") else list(data.get("hits", []))
    return []


def _best_sentence(excerpt: str, question: str) -> str:
    words = {w for w in re.findall(r"[a-z0-9]+", question.lower()) if w not in _STOP}
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", excerpt) if len(s.strip()) > 25]
    sentences = [s for s in sentences if "…" not in s and "..." not in s] or sentences
    if not sentences:
        return excerpt.strip()[:200]
    best = max(sentences, key=lambda s: len(words & set(re.findall(r"[a-z0-9]+", s.lower()))))
    return best[:240]


class OfflineModel:
    name = "offline-extractive"

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], force_tool: str | None = None
    ) -> ModelResponse:
        question = _question(messages)
        searches = sum(1 for m in messages if m["role"] == "tool" and '"hits"' in m["content"])
        failed = any(m["role"] == "tool" and "failed" in m["content"] for m in messages)
        hits = _last_hits(messages)
        if force_tool is None and searches == 0:
            return ModelResponse(
                None,
                [
                    _call("plan", {"sub_questions": [question[:200]]}),
                    _call("search_documents", {"query": question[:300]}),
                ],
                300,
                40,
            )
        if force_tool is None and not hits and searches == 1:
            keywords = " ".join(w for w in re.findall(r"[a-z0-9]+", question.lower()) if w not in _STOP)
            return ModelResponse(
                None, [_call("search_documents", {"query": f"{keywords} policy"[:300]})], 200, 20
            )
        if not hits or failed:
            answer = {
                "summary": "The policies I searched do not answer this question.",
                "claims": [],
                "notices": [{"kind": "missing_evidence", "text": "No supporting passage was found."}],
            }
        else:
            top = hits[0]
            quote = _best_sentence(top["excerpt"], question)
            answer = {
                "summary": f"{quote} ({top['title']}, p.{top['page']})",
                "claims": [{"text": quote, "evidence_ids": [top["evidence_id"]], "quote": quote}],
            }
        return ModelResponse(None, [_call("final_answer", answer)], 500, 80)
