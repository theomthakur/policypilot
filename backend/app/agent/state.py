"""Typed agent run state and the event emitter interface."""

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.agent.verifier import EvidenceItem


class Emitter(Protocol):
    async def __call__(self, type: str, status: str = "ok", **fields: Any) -> None: ...


@dataclass
class QuestionContext:
    question: str
    history: list[tuple[str, str]] = field(default_factory=list)  # (question, answer summary)
    clarification: tuple[str, str] | None = None  # (clarifying question asked, user's reply)
    original_question: str | None = None
    cited: frozenset[tuple[str, int]] = frozenset()  # (document_id, page) used in recent answers


@dataclass
class Totals:
    steps: int = 0
    tool_calls: int = 0
    query_revisions: int = 0
    retries: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "steps": self.steps,
            "tool_calls": self.tool_calls,
            "query_revisions": self.query_revisions,
            "retries": self.retries,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "model": self.model,
        }


@dataclass
class Outcome:
    stop_reason: str
    answer: dict[str, Any] | None = None
    clarification: dict[str, Any] | None = None
    totals: Totals = field(default_factory=Totals)
    ledger: dict[str, EvidenceItem] = field(default_factory=dict)


@dataclass
class RunState:
    ledger: dict[str, EvidenceItem] = field(default_factory=dict)
    key_of: dict[tuple[uuid.UUID, int], str] = field(default_factory=dict)
    seen_calls: set[str] = field(default_factory=set)
    flagged: set[str] = field(default_factory=set)
    last_query: str | None = None
    last_search_weak: bool = False
    last_search_reason: str = "no_hits"
    tool_failures: int = 0
    ledger_has_good: bool = False  # an earlier search in this turn already found on-topic material
    weak_revisions: int = 0
    planned: bool = False
    repair_used: bool = False
    nudges: int = 0

    def evidence_key(self, document_id: uuid.UUID, title: str, page: int) -> str:
        slot = (document_id, page)
        if slot not in self.key_of:
            key = f"E{len(self.key_of) + 1}"
            self.key_of[slot] = key
            self.ledger[key] = EvidenceItem(key, document_id, title, page)
        return self.key_of[slot]
