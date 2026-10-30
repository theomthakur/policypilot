"""The single-pass baseline for the evaluation: retrieve once on the raw question, generate once.

Same model, corpus, retrieval settings and temperature as the agent. No planning, no re-retrieval, no
clarification, no tool loop. Citations go through the same verifier, without a repair step.
"""

import json
import logging
import time
import uuid
from typing import Any

from app.agent import prompts
from app.agent.state import Emitter, Outcome, QuestionContext, RunState, Totals
from app.agent.verifier import PageText, sanitize_final_answer, verify_answer
from app.config import Settings
from app.llm.client import ChatModel
from app.tools.contracts import FinalAnswerInput, openai_tool_specs
from app.tools.impl import ToolContext, run_tool

logger = logging.getLogger("policypilot.baseline")


async def run_baseline(
    settings: Settings,
    model: ChatModel,
    tools: ToolContext,
    emit: Emitter,
    page_text: PageText,
    ctx: QuestionContext,
) -> Outcome:
    totals, state = Totals(model=model.name), RunState()
    await emit("turn_started", "info", state="PLAN", summary="Baseline: retrieve once, generate once.")

    began = time.monotonic()
    args = {"query": ctx.question[:300], "top_k": 5}
    await emit(
        "tool_call",
        "ok",
        state="ACT",
        tool="search_documents",
        input=args,
        attempt=1,
        summary="Calling search_documents.",
    )
    result = await run_tool(tools, "search_documents", args)
    totals.tool_calls = totals.tool_attempts = 1
    await emit(
        "tool_result",
        result.status,
        state="OBSERVE",
        tool="search_documents",
        attempt=1,
        duration_ms=round((time.monotonic() - began) * 1000),
        summary=result.summary,
    )

    hits = (result.data or {}).get("hits", [])
    shown = []
    for hit in hits:
        key = state.evidence_key(uuid.UUID(hit["document_id"]), hit["title"], hit["page"])
        shown.append({"evidence_id": key, "title": hit["title"], "page": hit["page"], "text": hit["excerpt"]})
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": prompts.load("baseline")},
        {
            "role": "user",
            "content": f"Question: {ctx.question}\n\nSearch results (untrusted data):\n"
            + json.dumps(shown, ensure_ascii=False),
        },
    ]
    began = time.monotonic()
    response = await model.complete(messages, openai_tool_specs(False), "final_answer")
    totals.steps = totals.model_requests = 1
    totals.prompt_tokens, totals.completion_tokens = response.prompt_tokens, response.completion_tokens
    await emit(
        "evaluate",
        "info",
        state="EVALUATE",
        summary="Model produced the answer.",
        duration_ms=round((time.monotonic() - began) * 1000),
        tokens={"prompt": response.prompt_tokens, "completion": response.completion_tokens},
    )

    call = next((c for c in response.tool_calls if c.name == "final_answer"), None)
    if call is None:
        logger.warning("baseline: the model did not call final_answer: %s", str(response.content)[:200])
        return Outcome("error", None, None, totals, state.ledger)
    try:
        draft = FinalAnswerInput.model_validate(sanitize_final_answer(call.arguments))
    except Exception as exc:
        logger.warning(
            "baseline: invalid final_answer: %s | args=%s", str(exc)[:300], str(call.arguments)[:300]
        )
        return Outcome("error", None, None, totals, state.ledger)
    verified = await verify_answer(draft, state.ledger, page_text)
    answer = verified.answer
    await emit(
        "verify",
        "ok" if verified.ok else "weak",
        state="VERIFY",
        summary="All citations verified." if verified.ok else f"{len(verified.failures)} check(s) failed.",
    )
    await emit(
        "answer", "ok", state="EMIT", summary=answer["summary"][:300], stop_reason=answer["stop_reason"]
    )
    return Outcome(answer["stop_reason"], answer, None, totals, state.ledger)
