"""Runs one turn as a durable job: builds context, runs the agent or baseline, persists everything.

The request that starts a turn returns immediately; the trace is written to trace_events as it happens,
so the SSE endpoint and the polling endpoint both read the same rows.
"""

import logging
import time
import uuid
from typing import Any

from sqlalchemy import func, select

from app.agent import prompts
from app.agent.baseline import run_baseline
from app.agent.loop import AgentRun
from app.agent.pages import PageCache
from app.agent.state import Outcome, QuestionContext, Totals
from app.config import Settings, get_settings
from app.db.models import Citation, Evidence, TraceEvent, Turn, utcnow
from app.db.session import get_sessionmaker
from app.llm.client import estimate_cost, get_model
from app.state import limits, session_state
from app.tools.impl import FaultInjector, ToolContext

logger = logging.getLogger("policypilot.turns")


class TracePersister:
    """Emitter that stores each event with the next sequence number and a real timestamp."""

    def __init__(self, turn_id: uuid.UUID, start_seq: int = 0) -> None:
        self.turn_id = turn_id
        self.seq = start_seq

    async def __call__(self, type: str, status: str = "ok", **fields: Any) -> None:
        payload = {"status": status, **{k: v for k, v in fields.items() if v is not None}}
        async with get_sessionmaker()() as db:
            db.add(TraceEvent(turn_id=self.turn_id, seq=self.seq, type=type, payload=payload))
            await db.commit()
        self.seq += 1


async def _build_context(turn: Turn, reply_to: uuid.UUID | None) -> QuestionContext:
    async with get_sessionmaker()() as db:
        state = await session_state.load(db, turn.session_id) or session_state.empty()
    history = [(h[0], h[1]) for h in state["history"]]
    cited = frozenset((str(d), int(pg)) for h in state["history"][-2:] if len(h) > 2 for d, pg in h[2])
    ctx = QuestionContext(turn.question, history, cited=cited)
    pending = state.get("pending_clarification")
    if reply_to is not None and pending and pending.get("turn_id") == str(reply_to):
        ctx.clarification = (pending["question"], turn.question)
        ctx.original_question = pending["original_question"]
    return ctx


async def run_turn(
    turn_id: uuid.UUID, session_id: uuid.UUID, fault: str | None, reply_to: uuid.UUID | None
) -> None:
    settings = get_settings()
    started = time.monotonic()
    outcome: Outcome
    async with get_sessionmaker()() as db:
        turn = await db.get(Turn, turn_id)
        if turn is None or turn.status != "running":
            return  # a duplicate delivery of a finished turn: one final answer only
        next_seq = (
            await db.execute(
                select(func.coalesce(func.max(TraceEvent.seq), -1)).where(TraceEvent.turn_id == turn_id)
            )
        ).scalar_one() + 1
    emit = TracePersister(turn_id, next_seq)
    if next_seq > 0:
        # The first attempt was cut short (crash or restart). Say so, then run again from the question.
        await emit(
            "turn_resumed",
            "info",
            state="PLAN",
            summary="The earlier attempt was interrupted, so this turn is starting over.",
        )
    try:
        async with get_sessionmaker()() as db:
            exhausted = await limits.budget_exhausted(db)
        if exhausted:
            await emit("turn_started", "info", state="PLAN", summary="Turn started.")
            await emit(
                "limit_reached",
                "info",
                state="PARTIAL_ANSWER",
                limit={"name": "budget"},
                summary="The daily demo budget is used up.",
            )
            outcome = Outcome("budget_exhausted", _budget_answer(), None, Totals())
        elif not settings.llm_configured:
            raise RuntimeError("LLM is not configured (set LLM_API_KEY).")
        else:
            outcome = await _execute(settings, turn, emit, fault, reply_to)
    except Exception as exc:
        logger.exception("turn failed", extra={"fields": {"turn_id": str(turn_id)}})
        await emit(
            "limit_reached", "error", state="PARTIAL_ANSWER", summary=f"Turn failed: {type(exc).__name__}"
        )
        outcome = Outcome("error", _error_answer(), None, Totals())
    await _finish(settings, turn, emit, outcome, int((time.monotonic() - started) * 1000))


async def _execute(
    settings: Settings, turn: Turn, emit: TracePersister, fault: str | None, reply_to: uuid.UUID | None
) -> Outcome:
    ctx = await _build_context(turn, reply_to)
    model = get_model()
    tools = ToolContext(settings, turn.session_id, FaultInjector(fault, settings.fault_injection_enabled))
    pages = PageCache()
    if turn.mode == "baseline":
        return await run_baseline(settings, model, tools, emit, pages, ctx)
    return await AgentRun(settings, model, tools, emit, pages).run(ctx)


def _budget_answer() -> dict[str, Any]:
    return {
        "summary": "The daily demo budget has been used up, so no new questions can be answered today.",
        "claims": [],
        "citations": [],
        "notices": [{"kind": "partial", "text": "Try again tomorrow.", "citation_indexes": []}],
        "unverified_claims": [],
        "stop_reason": "budget_exhausted",
        "partial": True,
    }


def _error_answer() -> dict[str, Any]:
    return {
        "summary": "Something went wrong while answering. No answer was produced.",
        "claims": [],
        "citations": [],
        "notices": [{"kind": "partial", "text": "The turn failed.", "citation_indexes": []}],
        "unverified_claims": [],
        "stop_reason": "error",
        "partial": True,
    }


async def _finish(
    settings: Settings, turn: Turn, emit: TracePersister, outcome: Outcome, latency_ms: int
) -> None:
    totals = outcome.totals.as_dict()
    cost = estimate_cost(settings, totals["prompt_tokens"], totals["completion_tokens"])
    totals |= {
        "latency_ms": latency_ms,
        "estimated_cost_usd": round(cost, 6),
        "prompt_version": prompts.PROMPT_VERSION,
    }
    await emit(
        "turn_completed",
        "info",
        summary=f"Finished: {outcome.stop_reason}.",
        stop_reason=outcome.stop_reason,
        duration_ms=latency_ms,
    )
    answer = outcome.answer
    async with get_sessionmaker()() as db:
        row = await db.get(Turn, turn.id, with_for_update=True)
        assert row is not None
        if row.status != "running":
            return  # another delivery finished this turn first; keep its answer
        row.status = "failed" if outcome.stop_reason == "error" else "completed"
        row.stop_reason, row.answer, row.clarification = outcome.stop_reason, answer, outcome.clarification
        row.totals, row.model, row.prompt_version = (
            totals,
            totals.get("model") or None,
            prompts.PROMPT_VERSION,
        )
        row.finished_at = utcnow()
        cited_slots = {(c["document_id"], c["page"]) for c in (answer or {}).get("citations", [])}
        for key, item in outcome.ledger.items():
            db.add(
                Evidence(
                    turn_id=turn.id,
                    evidence_key=key,
                    document_id=item.document_id,
                    page_number=item.page,
                    selected=(str(item.document_id), item.page) in cited_slots,
                )
            )
        key_of = {(str(i.document_id), i.page): k for k, i in outcome.ledger.items()}
        for citation in (answer or {}).get("citations", []):
            slot = (citation["document_id"], citation["page"])
            if slot in key_of:
                db.add(
                    Citation(
                        turn_id=turn.id,
                        claim_index=citation["index"],
                        document_id=uuid.UUID(citation["document_id"]),
                        page_number=citation["page"],
                        evidence_key=key_of[slot],
                        quote=citation["quote"],
                        verified=citation["verified"],
                        check=citation["check"],
                    )
                )
        await db.commit()
        state = await session_state.load(db, turn.session_id) or session_state.empty()
        if outcome.stop_reason == "clarification_needed" and outcome.clarification:
            state["pending_clarification"] = {
                "turn_id": str(turn.id),
                "question": outcome.clarification["question"],
                "original_question": turn.question,
            }
        else:
            state["pending_clarification"] = None
            if answer:
                sources = sorted({f"{c['title']} p.{c['page']}" for c in answer.get("citations", [])})
                note = f" [Sources: {'; '.join(sources)}]" if sources else ""
                pages = sorted({(c["document_id"], c["page"]) for c in answer.get("citations", [])})
                state["history"].append([turn.question, str(answer["summary"])[:450] + note, pages])
        await session_state.save(db, turn.session_id, state)
    await limits.add_spend(cost)


async def load_events(turn_id: uuid.UUID, after: int) -> list[TraceEvent]:
    async with get_sessionmaker()() as db:
        rows = await db.execute(
            select(TraceEvent)
            .where(TraceEvent.turn_id == turn_id, TraceEvent.seq > after)
            .order_by(TraceEvent.seq)
        )
        return list(rows.scalars())


async def mark_interrupted(turn_id: uuid.UUID) -> None:
    """The turn's job ran out of attempts after repeated crashes: end it with an honest failed answer."""
    async with get_sessionmaker()() as db:
        row = await db.get(Turn, turn_id, with_for_update=True)
        if row is None or row.status != "running":
            return
        next_seq = (
            await db.execute(
                select(func.coalesce(func.max(TraceEvent.seq), -1)).where(TraceEvent.turn_id == turn_id)
            )
        ).scalar_one() + 1
        answer = _error_answer()
        answer["summary"] = (
            "This question was interrupted more than once and could not be finished. Please ask it again."
        )
        row.status, row.stop_reason, row.answer, row.finished_at = "failed", "error", answer, utcnow()
        db.add(
            TraceEvent(
                turn_id=turn_id,
                seq=next_seq,
                type="turn_completed",
                payload={"status": "info", "summary": "Finished: interrupted.", "stop_reason": "error"},
            )
        )
        await db.commit()
