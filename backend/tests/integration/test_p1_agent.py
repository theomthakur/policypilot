"""P1 behaviors: structured clarification, abstention, policy-family discovery and conflict notices,
follow-up scoping, truthful counters and the turn deadline. A scripted model drives the real loop."""

import asyncio
import json
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlalchemy import select

from tests.integration.conftest import clear_caches
from tests.integration.test_agent import GUEST, QUOTE_MBPS, REMOTE, Collector, _answer_step, _load

NEW_POLICY = ["1. Password Standard\n\nPasswords must not expire on a schedule. Expiration is prohibited."]
OLD_POLICY = ["1. Password Policy\n\nPasswords must be changed every 90 days under the rotation rule."]
QUOTE_NEW = "Passwords must not expire on a schedule."
QUOTE_OLD = "Passwords must be changed every 90 days under the rotation rule."


def _run(
    model: Any,
    question: str,
    ctx_kwargs: dict[str, Any] | None = None,
    fault: str | None = None,
    **overrides: Any,
) -> tuple[Any, Collector]:
    from app.agent.loop import AgentRun
    from app.agent.pages import PageCache
    from app.agent.state import QuestionContext
    from app.config import get_settings
    from app.tools.impl import FaultInjector, ToolContext

    settings = get_settings().model_copy(update={"fault_injection_enabled": True, **overrides})
    emit = Collector()
    tools = ToolContext(settings, None, FaultInjector(fault, True))
    context = QuestionContext(question, **(ctx_kwargs or {}))

    async def go() -> Any:
        return await AgentRun(settings, model, tools, emit, PageCache()).run(context)

    clear_caches()
    outcome = asyncio.run(go())
    clear_caches()
    return outcome, emit


def _assess(answerable: bool, **fields: Any) -> Any:
    from app.llm.client import respond

    return respond(("assess_question", {"answerable": answerable, **fields}))


def _document_id(filename_part: str) -> str:
    from app.db.models import Document
    from app.db.session import get_sessionmaker

    async def go() -> str:
        async with get_sessionmaker()() as db:
            docs = (await db.execute(select(Document))).scalars().all()
            return str(next(d.id for d in docs if filename_part in d.filename))

    clear_caches()
    found = asyncio.run(go())
    clear_caches()
    return found


# ---- P1-A: the code acts on a structured ambiguity assessment -------------------------------------


RENEWAL = [
    "1. Account Renewal\n\nStudent accounts renew automatically each term without any form.\n\n"
    "Sponsored guest accounts renew only when the sponsor submits the renewal form."
]


def _load_renewal(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.ingest.pipeline import ensure_corpus_loaded

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_pdf(RENEWAL, name="corpus/08-renewal.pdf")
    make_pdf(REMOTE, name="corpus/02-remote.pdf")
    clear_caches()
    asyncio.run(ensure_corpus_loaded(corpus))
    clear_caches()


def _renewal_assessment(**overrides: Any) -> Any:
    fields: dict[str, Any] = {
        "answers_differ": True,
        "missing_slot": "account type",
        "interpretations": [
            {"label": "Student account", "quote": "Student accounts renew automatically each term"},
            {
                "label": "Sponsored guest account",
                "quote": "Sponsored guest accounts renew only when the sponsor",
            },
        ],
        "clarification_question": "Which type of account do you want to renew?",
    }
    return _assess(False, **{**fields, **overrides})


def test_parallel_cases_in_one_document_make_the_loop_ask(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_renewal(make_pdf, tmp_path)
    model = ScriptedModel([respond(("search_documents", {"query": "renew account"})), _renewal_assessment()])
    outcome, events = _run(model, "How do I renew my account?", agent_assess_ambiguity=True)
    assert outcome.stop_reason == "clarification_needed"
    assert outcome.clarification == {
        "question": "Which type of account do you want to renew?",
        "options": ["Student account", "Sponsored guest account"],
    }
    assessment = events.of("assessment")[0]["assessment"]
    assert assessment["answerable"] is False and assessment["supported"] == 2
    assert outcome.totals.model_requests == 2 and outcome.totals.steps == 1


def test_variants_from_different_documents_are_not_one_ambiguity(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth VPN exceptions approved"})),
            _assess(
                False,
                missing_slot="topic",
                interpretations=[
                    {"label": "Guest network", "quote": "limited to 10 Mbps download and 2 Mbps upload"},
                    {
                        "label": "VPN exceptions",
                        "quote": "VPN exceptions are approved by the Chief Information",
                    },
                ],
                clarification_question="Which one?",
            ),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(model, "q", agent_assess_ambiguity=True)
    assert outcome.stop_reason == "answered" and not events.of("clarification_requested")


def test_a_case_the_user_already_named_is_never_asked_about(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_renewal(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "renew sponsored guest account"})),
            _renewal_assessment(),
            respond(("final_answer", {"summary": "The documents do not contain this."})),
        ]
    )
    outcome, events = _run(model, "How does a sponsored guest renew?", agent_assess_ambiguity=True)
    assert not events.of("clarification_requested") and outcome.stop_reason != "clarification_needed"


def test_the_three_judgments_must_all_point_to_asking(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_renewal(make_pdf, tmp_path)
    grounded = {
        "default_reading": "everyone",
        "default_quote": "Student accounts renew automatically each term without any form",
    }
    for overrides in ({"answers_differ": False}, {"value_in_question": "students"}, grounded):
        model = ScriptedModel(
            [
                respond(("search_documents", {"query": "renew account"})),
                _renewal_assessment(**overrides),
                respond(("final_answer", {"summary": "The documents do not contain this."})),
            ]
        )
        outcome, _ = _run(model, "How do I renew my account?", agent_assess_ambiguity=True)
        assert outcome.stop_reason != "clarification_needed", overrides


def test_quotes_worded_alike_are_one_rule_not_two(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_renewal(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "renew account"})),
            _renewal_assessment(
                interpretations=[
                    {"label": "Student account", "quote": "Student accounts renew automatically each term"},
                    {
                        "label": "Sponsored guest account",
                        "quote": "Student accounts renew automatically each term",
                    },
                ]
            ),
            respond(("final_answer", {"summary": "The documents do not contain this."})),
        ]
    )
    outcome, _ = _run(model, "How do I renew my account?", agent_assess_ambiguity=True)
    assert outcome.stop_reason != "clarification_needed"


def test_a_label_that_is_not_about_its_passage_is_not_trusted(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_renewal(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "renew account"})),
            _renewal_assessment(
                interpretations=[
                    {"label": "Alumni network", "quote": "Student accounts renew automatically each term"},
                    {"label": "Contractors", "quote": "Sponsored guest accounts renew only when the sponsor"},
                ]
            ),
            respond(("final_answer", {"summary": "The documents do not contain this."})),
        ]
    )
    outcome, events = _run(model, "How do I renew my account?", agent_assess_ambiguity=True)
    assert (
        outcome.stop_reason != "clarification_needed"
        and events.of("assessment")[0]["assessment"]["supported"] == 0
    )


def test_interpretations_that_are_not_in_the_results_never_trigger_a_question(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth VPN exceptions approved"})),
            _assess(
                False,
                missing_slot="user role",
                interpretations=[
                    {"label": "Faculty", "quote": "Faculty members receive unlimited bandwidth"},
                    {"label": "Alumni", "quote": "Alumni may connect for one hour per day"},
                ],
                clarification_question="Which role are you?",
            ),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(model, "What is the guest bandwidth?", agent_assess_ambiguity=True)
    assert outcome.stop_reason == "answered" and not events.of("clarification_requested")
    assert events.of("assessment")[0]["assessment"]["supported"] == 0


def test_specific_question_is_not_interrupted_by_the_assessment(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth"})),
            _assess(True),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(model, "What is the guest bandwidth?", agent_assess_ambiguity=True)
    assert outcome.stop_reason == "answered" and not events.of("clarification_requested")
    assert events.of("assessment")[0]["assessment"]["answerable"] is True
    assert outcome.totals.model_requests == 3  # search, assessment, answer


def test_a_single_interpretation_never_triggers_a_question(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth"})),
            _assess(
                False,
                interpretations=[{"label": "Only one", "quote": "limited to 10 Mbps"}],
                clarification_question="Which?",
            ),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, _ = _run(model, "q", agent_assess_ambiguity=True)
    assert outcome.stop_reason == "answered"


def test_no_assessment_after_a_clarification_reply_or_with_history(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    for kwargs in (
        {"clarification": ("Which account?", "Student"), "original_question": "Renew my account"},
        {"history": [("Earlier question", "Earlier answer")]},
    ):
        model = ScriptedModel(
            [
                respond(("search_documents", {"query": "guest network bandwidth"})),
                _answer_step("Guest", 1, QUOTE_MBPS),
            ]
        )
        outcome, events = _run(model, "q", ctx_kwargs=kwargs, agent_assess_ambiguity=True)
        assert outcome.stop_reason == "answered" and not events.of("assessment")


def test_a_failed_assessment_never_blocks_the_answer(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth"})),
            respond(),  # no tool call at all
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, _ = _run(model, "q", agent_assess_ambiguity=True)
    assert outcome.stop_reason == "answered"


# ---- P1-B: abstentions are normalized in code -------------------------------------------------------


def test_abstention_gets_a_missing_evidence_notice_and_no_citations(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "internet reimbursement"})),
            respond(("final_answer", {"summary": "The documents do not contain a reimbursement amount."})),
        ]
    )
    outcome, _ = _run(model, "How much is the internet reimbursement?")
    answer = outcome.answer
    assert outcome.stop_reason == "insufficient_evidence"
    assert answer["claims"] == [] and answer["citations"] == [] and answer["partial"] is False
    assert [n["kind"] for n in answer["notices"]] == ["missing_evidence"]


# ---- P1-C: policy families, metadata and conflict notices -----------------------------------------------


def _metadata_corpus(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.ingest.pipeline import ensure_corpus_loaded

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_pdf(OLD_POLICY, name="corpus/04-password-2023.pdf")
    make_pdf(NEW_POLICY, name="corpus/05-identity-2025.pdf")
    make_pdf(GUEST, name="corpus/01-guest.pdf")
    (corpus / "metadata.json").write_text(
        json.dumps(
            {
                "04-password-2023.pdf": {
                    "authority": "institutional",
                    "version": "4.0",
                    "effective_date": "2023-08-01",
                    "doc_family": "identity",
                },
                "05-identity-2025.pdf": {
                    "authority": "institutional",
                    "version": "1.0",
                    "effective_date": "2025-01-15",
                    "doc_family": "identity",
                    "supersedes": [
                        {
                            "filename": "04-password-2023.pdf",
                            "scope": "partial",
                            "statement": "states that it supersedes the password expiration provisions",
                            "scope_terms": [
                                "expire",
                                "expiration",
                                "90 days",
                                "rotation",
                                "change their password",
                            ],
                            "exception_terms": ["service account"],
                        }
                    ],
                },
                "01-guest.pdf": {"authority": "institutional", "doc_family": "network"},
            }
        )
    )
    clear_caches()
    asyncio.run(ensure_corpus_loaded(corpus))
    clear_caches()


def _two_claim_step() -> Callable[[list[dict[str, Any]]], Any]:
    from app.llm.client import respond
    from tests.integration.test_agent import _evidence_id

    def step(messages: list[dict[str, Any]]) -> Any:
        new, old = (
            _evidence_id(messages, "Password Standard", 1),
            _evidence_id(messages, "Password Policy", 1),
        )
        return respond(
            (
                "final_answer",
                {
                    "summary": "The 2023 policy rotates passwords; the 2025 standard prohibits expiration.",
                    "claims": [
                        {"text": "2025 prohibits expiry.", "evidence_ids": [new], "quote": QUOTE_NEW},
                        {"text": "2023 rotates every 90 days.", "evidence_ids": [old], "quote": QUOTE_OLD},
                    ],
                },
            )
        )

    return step


def test_search_adds_the_other_version_of_a_policy_family_with_metadata(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _metadata_corpus(make_pdf, tmp_path)
    model = ScriptedModel(
        [respond(("search_documents", {"query": "passwords must not expire prohibited"})), _two_claim_step()]
    )
    outcome, events = _run(model, "Do passwords expire?")
    hits = events.of("tool_result")[0]["result"]["pages"]
    titles = {h["title"] for h in hits}
    assert {"1. Password Standard", "1. Password Policy"} <= titles, titles
    assert outcome.stop_reason == "answered"


def test_citing_a_document_and_the_one_it_supersedes_adds_a_conflict_notice(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _metadata_corpus(make_pdf, tmp_path)
    model = ScriptedModel(
        [respond(("search_documents", {"query": "passwords must not expire prohibited"})), _two_claim_step()]
    )
    outcome, _ = _run(model, "Do passwords expire?")
    notices = [n for n in outcome.answer["notices"] if n["kind"] == "conflict"]
    assert len(notices) == 1
    assert notices[0]["citation_indexes"] == [1, 2]
    assert "2025-01-15" in notices[0]["text"] and "2023-08-01" in notices[0]["text"]
    assert "states that it supersedes" in notices[0]["text"]


def test_an_answer_that_ignores_the_superseding_document_is_sent_back_once(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond
    from tests.integration.test_agent import _evidence_id

    _metadata_corpus(make_pdf, tmp_path)

    def only_old(messages: list[dict[str, Any]]) -> Any:
        old = _evidence_id(messages, "Password Policy", 1)
        return respond(
            (
                "final_answer",
                {
                    "summary": "Yes, every 90 days.",
                    "claims": [{"text": "Every 90 days.", "evidence_ids": [old], "quote": QUOTE_OLD}],
                },
            )
        )

    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "passwords must not expire prohibited"})),
            only_old,
            _two_claim_step(),
        ]
    )
    outcome, _ = _run(model, "Do passwords expire?")
    sent_back = [m for m in model.calls[-1] if m["role"] == "tool" and "effective 2025-01-15" in m["content"]]
    assert sent_back and "conflict" in sent_back[0]["content"]
    assert len(outcome.answer["citations"]) == 2
    assert [n["kind"] for n in outcome.answer["notices"]] == ["conflict"]


def test_no_conflict_notice_without_a_documented_relation(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth"})),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, _ = _run(model, "q")
    assert not [n for n in outcome.answer["notices"] if n["kind"] == "conflict"]


# ---- P1-E: follow-ups search the earlier sources first, then everything -----------------------------------


def test_follow_up_search_is_scoped_to_earlier_sources(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    guest = _document_id("01-guest")
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network limits"})),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(
        model,
        "And what else?",
        ctx_kwargs={"history": [("q", "a")], "cited": frozenset({(guest, 1)})},
    )
    scopes = [e.get("scope") for e in events.of("tool_call")]
    assert scopes == ["previous_sources"] and outcome.stop_reason == "answered"
    assert {h["title"] for h in events.of("tool_result")[0]["result"]["pages"]} == {
        outcome.answer["citations"][0]["title"]
    }


def test_follow_up_on_a_new_topic_falls_back_to_all_documents(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    remote = _document_id("02-remote")
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth mbps"})),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(
        model,
        "What is the guest bandwidth?",
        ctx_kwargs={"history": [("q", "a")], "cited": frozenset({(remote, 1)})},
    )
    assert [e.get("scope") for e in events.of("tool_call")] == ["previous_sources", "all_documents"]
    assert outcome.stop_reason == "answered"
    assert outcome.totals.tool_calls == 1 and outcome.totals.tool_attempts == 2


# ---- P1-F: truthful counters and the turn deadline ------------------------------------------------------

# ---- P1-F: truthful counters and the turn deadline -----------------------------------------------------


def test_counters_separate_logical_calls_attempts_retries_and_blocks(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    same = {"query": "guest network bandwidth"}
    model = ScriptedModel(
        [
            respond(("search_documents", same)),
            respond(("search_documents", same)),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, _ = _run(model, "q", fault="search_documents:timeout:1", agent_tool_timeout_s=0.3)
    t = outcome.totals
    assert (t.tool_calls, t.tool_attempts, t.retries, t.blocked_calls) == (1, 2, 1, 1)
    assert t.model_requests == 3


def test_the_turn_deadline_caps_a_slow_tool_and_stops_retries(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel([respond(("search_documents", {"query": "guest network bandwidth"}))])
    began = time.monotonic()
    outcome, _ = _run(
        model, "q", fault="search_documents:timeout:5", agent_tool_timeout_s=30.0, agent_turn_timeout_s=1.0
    )
    assert time.monotonic() - began < 5  # the 30 s tool timeout did not outlive the 1 s turn
    assert outcome.totals.retries == 0 and outcome.totals.tool_attempts == 1
    assert outcome.answer["partial"] is True and uuid.UUID(int=0)  # ended with an honest partial answer


def _template_run(question: str) -> tuple[Any, Collector]:
    from app.llm.client import ScriptedModel, respond

    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "passwords expire change prohibited"})),
            _two_claim_step(),
        ]
    )
    return _run(model, question)


def test_current_rule_questions_are_answered_from_both_passages_by_code(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    _metadata_corpus(make_pdf, tmp_path)
    outcome, events = _template_run(
        "Do users have to change their password on a schedule, or does it expire?"
    )
    answer = outcome.answer
    assert [c["page"] for c in answer["citations"]] == [1, 1] and len(answer["citations"]) == 2
    assert "expire on a schedule" in answer["summary"] and "90 days" in answer["summary"]
    assert [n["kind"] for n in answer["notices"]] == ["conflict"] and answer["stop_reason"] == "answered"
    assert any("answering from both passages" in e.get("summary", "") for e in events.of("evaluate"))


def test_a_historical_question_is_not_overridden(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    _metadata_corpus(make_pdf, tmp_path)
    outcome, events = _template_run("Did the 2023 policy say passwords expire?")
    assert not any("answering from both passages" in e.get("summary", "") for e in events.of("evaluate"))
    assert outcome.answer["summary"].startswith("The 2023 policy rotates")  # the model's own answer stands


def test_a_provision_the_document_excepts_is_not_overridden(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    _metadata_corpus(make_pdf, tmp_path)
    outcome, events = _template_run("Do service account passwords expire?")
    assert not any("answering from both passages" in e.get("summary", "") for e in events.of("evaluate"))
    assert outcome.answer["summary"].startswith("The 2023 policy rotates")


def test_a_summary_sentence_with_a_figure_the_pages_lack_is_removed(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond
    from tests.integration.test_agent import _evidence_id

    _load(make_pdf, tmp_path)

    def invented(messages: list[dict[str, Any]]) -> Any:
        key = _evidence_id(messages, "Guest", 1)
        return respond(
            (
                "final_answer",
                {
                    "summary": "Guests get 10 Mbps down and 2 Mbps up. Sessions last 48 hours. Ask the desk.",
                    "claims": [{"text": "Guests get 10 Mbps.", "evidence_ids": [key], "quote": QUOTE_MBPS}],
                },
            )
        )

    model = ScriptedModel([respond(("search_documents", {"query": "guest network bandwidth"})), invented])
    outcome, _ = _run(model, "What is the guest limit?")
    summary = outcome.answer["summary"]
    assert "10 Mbps" in summary and "48 hours" not in summary and "Ask the desk" in summary
    assert any("removed" in n["text"] for n in outcome.answer["notices"])


def test_a_skipped_assessment_is_visible_in_the_trace(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth"})),
            respond(
                ("assess_question", {"answerable": True, "surprise_field": "x"})
            ),  # invalid for the schema
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(model, "q", agent_assess_ambiguity=True)
    assert outcome.stop_reason == "answered"
    assert events.of("assessment")[0]["assessment"]["skipped"] == "ValidationError"


def test_the_conflict_repair_respects_documented_exceptions(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond
    from tests.integration.test_agent import _evidence_id

    _metadata_corpus(make_pdf, tmp_path)

    def only_old(messages: list[dict[str, Any]]) -> Any:
        old = _evidence_id(messages, "Password Policy", 1)
        return respond(
            (
                "final_answer",
                {
                    "summary": "Service accounts rotate every 90 days.",
                    "claims": [{"text": "Every 90 days.", "evidence_ids": [old], "quote": QUOTE_OLD}],
                },
            )
        )

    model = ScriptedModel([respond(("search_documents", {"query": "passwords expire prohibited"})), only_old])
    outcome, _ = _run(model, "How often must service account passwords expire?")
    assert len(model.calls) == 2  # no repair round trip: the exception keeps the supersession out of it
    assert [n["kind"] for n in outcome.answer["notices"]] == []


def test_a_failed_quote_is_repaired_from_the_pages_own_words(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond
    from tests.integration.test_agent import _evidence_id

    _load(make_pdf, tmp_path)

    def near_miss(messages: list[dict[str, Any]]) -> Any:
        key = _evidence_id(messages, "Guest", 1)
        return respond(
            (
                "final_answer",
                {
                    "summary": "Guests are limited.",
                    "claims": [
                        {
                            "text": "Guests are limited.",
                            "evidence_ids": [key],
                            "quote": "the guest network is capped at 10 Mbps down",
                        }
                    ],
                },
            )
        )

    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth"})),
            near_miss,
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(model, "q")
    repair = [m for m in model.calls[-1] if m["role"] == "tool" and "closest text" in m["content"]]
    assert repair and "10 Mbps download and 2 Mbps upload" in repair[0]["content"]
    assert events.of("verify")[0]["failed_checks"] and outcome.stop_reason == "answered"


def test_a_claim_with_a_figure_the_cited_page_lacks_is_rejected(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond
    from tests.integration.test_agent import _evidence_id

    _load(make_pdf, tmp_path)

    def invented(messages: list[dict[str, Any]]) -> Any:
        key = _evidence_id(messages, "Guest", 1)
        return respond(
            (
                "final_answer",
                {
                    "summary": "Guests get 99 Mbps.",
                    "claims": [{"text": "Guests get 99 Mbps.", "evidence_ids": [key], "quote": QUOTE_MBPS}],
                },
            )
        )

    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network bandwidth"})),
            invented,
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(model, "q")
    assert "figure 99" in events.of("verify")[0]["failed_checks"][0]
    assert outcome.stop_reason == "answered" and "99" not in outcome.answer["summary"]


def test_a_default_without_a_quote_does_not_stop_a_clarifying_question(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_renewal(make_pdf, tmp_path)
    for fields, expect_ask in (
        ({"default_reading": "all accounts"}, True),  # asserted, no quote: ignored
        (
            {"default_reading": "all accounts", "default_quote": "Accounts renew each term for everybody"},
            True,
        ),  # quote not in results
        (
            {"default_reading": "student", "default_quote": "Student accounts renew automatically each term"},
            True,
        ),  # a variant's own quote
        (
            {
                "default_reading": "everyone",
                "default_quote": "Student accounts renew automatically each term without any form",
            },
            False,
        ),  # a grounded default
    ):
        model = ScriptedModel(
            [
                respond(("search_documents", {"query": "renew account"})),
                _renewal_assessment(**fields),
                respond(("final_answer", {"summary": "The documents do not contain this."})),
            ]
        )
        outcome, _ = _run(model, "How do I renew my account?", agent_assess_ambiguity=True)
        assert (outcome.stop_reason == "clarification_needed") is expect_ask, fields


def test_the_judge_also_sees_passages_for_the_users_exact_words(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_renewal(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(
                ("search_documents", {"query": "membership terms"})
            ),  # the model's query drops the user's words
            _assess(True),
            respond(("final_answer", {"summary": "The documents do not contain this."})),
        ]
    )
    outcome, events = _run(model, "How do I renew my account?", agent_assess_ambiguity=True)
    literal = [e for e in events.of("tool_call") if e.get("scope") == "literal_question"]
    assert len(literal) == 1 and literal[0]["input"]["query"] == "How do I renew my account?"
    assert outcome.totals.tool_calls == 2 and outcome.totals.tool_attempts == 2
    judge_input = model.calls[1][-1]["content"]
    assert "Student accounts renew automatically" in judge_input  # only the literal search finds this passage
