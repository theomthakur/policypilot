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
        "question": "Which one do you mean: Student account or Sponsored guest account?",
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


def test_evidence_backed_variants_override_a_false_difference_boolean(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_renewal(make_pdf, tmp_path)
    grounded = {
        "default_reading": "everyone",
        "default_quote": "Student accounts renew automatically each term without any form",
    }
    # The judge's `answers_differ` is advisory: if its own quoted, verified variants show two different
    # rules, deterministic code asks instead of silently guessing.
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "renew account"})),
            _renewal_assessment(answers_differ=False),
        ]
    )
    outcome, events = _run(model, "How do I renew my account?", agent_assess_ambiguity=True)
    assert outcome.stop_reason == "clarification_needed"
    assessment = events.of("assessment")[0]["assessment"]
    assert assessment["judge_answers_differ"] is False and assessment["evidence_rules_differ"] is True

    # A named value or a grounded default still prevents needless clarification.
    for overrides in ({"value_in_question": "students"}, grounded):
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


def test_variant_relevance_accepts_a_matching_result_excerpt() -> None:
    """A branch rule may not repeat the policy topic, even when its result excerpt does."""
    from app.agent.loop import AgentRun
    from app.tools.contracts import AssessQuestionInput

    run = AgentRun.__new__(AgentRun)
    run.question = "What are the records retention requirements?"
    verdict = AssessQuestionInput.model_validate(
        {
            "answerable": False,
            "interpretations": [
                {"label": "Student records", "quote": "Student records are retained for 7 years."},
                {"label": "Faculty records", "quote": "Faculty records are retained for 10 years."},
            ],
        }
    )
    hits = [
        {
            "document_id": "retention-policy",
            "page": 1,
            "excerpt": "Records retention requirements. Student records are retained for 7 years.",
        },
        {
            "document_id": "retention-policy",
            "page": 2,
            "excerpt": "Records retention requirements. Faculty records are retained for 10 years.",
        },
    ]

    variants = run._backed_variants(verdict, hits)

    assert [entry["label"] for entry in variants.options] == ["Student records", "Faculty records"]


def test_generic_location_name_does_not_count_as_a_named_variant() -> None:
    """A shared institution name cannot suppress a needed clarification."""
    from app.agent.loop import _GENERIC_STEMS, _tokens

    labels = [_tokens("Northfield student account"), _tokens("Sponsored account")]
    unique = [
        (tokens - set().union(*(other for other in labels if other is not tokens))) - _GENERIC_STEMS
        for tokens in labels
    ]

    assert not (_tokens("Northfield account") & set().union(*unique))


def test_variant_scan_continues_after_an_incomplete_duplicate_excerpt() -> None:
    """A later result can contain the label that an earlier duplicate excerpt omitted."""
    from app.agent.loop import AgentRun
    from app.tools.contracts import AssessQuestionInput

    run = AgentRun.__new__(AgentRun)
    run.question = "How do accounts renew?"
    verdict = AssessQuestionInput.model_validate(
        {
            "answerable": False,
            "interpretations": [
                {"label": "Student account", "quote": "renew automatically each term"},
            ],
        }
    )
    hits = [
        {
            "document_id": "renewal-policy",
            "page": 1,
            "excerpt": "Accounts renew automatically each term.",
        },
        {
            "document_id": "renewal-policy",
            "page": 2,
            "excerpt": "Student accounts renew automatically each term.",
        },
    ]

    variants = run._backed_variants(verdict, hits)

    assert variants.options[0]["page"] == 2


def test_auxiliary_words_are_not_ambiguity_relevance_tokens() -> None:
    from app.agent.loop import _tokens

    assert "get" not in _tokens("When does an inactive account get suspended?")


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


def test_question_with_an_explicit_policy_year_is_not_asked_to_choose_a_version(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    """A stated year already identifies the policy version requested."""
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "2023 password expiration"})),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )

    outcome, events = _run(
        model,
        "Did the 2023 policy say passwords expire?",
        agent_assess_ambiguity=True,
    )

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


def test_grounded_claims_drop_a_contradictory_missing_evidence_notice(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond
    from tests.integration.test_agent import _evidence_id

    _load(make_pdf, tmp_path)

    def mixed_answer(messages: list[dict[str, Any]]) -> Any:
        key = _evidence_id(messages, "Guest", 1)
        return respond(
            (
                "final_answer",
                {
                    "summary": "Guests are limited to 10 Mbps.",
                    "claims": [
                        {"text": "Guests are limited to 10 Mbps.", "evidence_ids": [key], "quote": QUOTE_MBPS}
                    ],
                    "notices": [{"kind": "missing_evidence", "text": "No details were found."}],
                },
            )
        )

    model = ScriptedModel([respond(("search_documents", {"query": "guest network bandwidth"})), mixed_answer])
    outcome, _ = _run(model, "What is the guest bandwidth?")
    assert outcome.stop_reason == "answered"
    assert not [n for n in outcome.answer["notices"] if n["kind"] == "missing_evidence"]


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


def test_documented_mfa_scope_is_eligible_for_conflict_handling() -> None:
    """The real 2023 and 2025 policies disagree about university-wide MFA."""
    from app.agent.loop import AgentRun

    metadata = json.loads((Path(__file__).parents[3] / "corpus" / "pdfs" / "metadata.json").read_text())
    relation = metadata["05-identity-mfa-standard-2025.pdf"]["supersedes"][0]
    run = AgentRun.__new__(AgentRun)
    run.question = "Is multi-factor authentication required for every Northfield account?"

    assert run._in_scope(relation, None) is True


def test_conflict_selection_prefers_a_universal_scope_statement() -> None:
    from types import SimpleNamespace

    from app.agent.loop import AgentRun
    from app.agent.state import RunState
    from app.agent.verifier import EvidenceItem

    doc_id = uuid.uuid4()
    run = AgentRun.__new__(AgentRun)
    run.question = "Is multi-factor authentication required for every account?"
    run.state = RunState(
        ledger={
            "E1": EvidenceItem("E1", doc_id, "Password policy", 4),
            "E2": EvidenceItem("E2", doc_id, "Password policy", 6),
        }
    )

    async def page_text(_: uuid.UUID, page: int) -> str:
        return {
            4: "Multi-factor authentication is available but not universally mandated for every account.",
            6: "Privileged accounts must use multi-factor authentication for all interactive logons.",
        }[page]

    run.page_text = page_text
    found = asyncio.run(run._best_sentence(SimpleNamespace(id=doc_id), ["mfa", "multi-factor", "rotation"]))
    assert found is not None
    assert found[0] == 4 and "not universally mandated" in found[1]


def test_conflict_evidence_is_refreshed_before_a_one_sided_answer(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond
    from tests.integration.test_agent import _evidence_id

    _metadata_corpus(make_pdf, tmp_path)

    def only_new(messages: list[dict[str, Any]]) -> Any:
        key = _evidence_id(messages, "Password Standard", 1)
        return respond(
            (
                "final_answer",
                {
                    "summary": "Passwords do not expire.",
                    "claims": [
                        {"text": "Passwords do not expire.", "evidence_ids": [key], "quote": QUOTE_NEW}
                    ],
                },
            )
        )

    model = ScriptedModel([respond(("search_documents", {"query": "passwords expire prohibited"})), only_new])
    outcome, events = _run(model, "Do passwords expire?")
    assert outcome.stop_reason == "answered"
    assert {c["title"] for c in outcome.answer["citations"]} == {"1. Password Standard", "1. Password Policy"}
    assert [n["kind"] for n in outcome.answer["notices"]] == ["conflict"]
    assert any(e.get("scope") == "policy_version_comparison" for e in events.of("tool_call"))


def test_complete_conflict_template_is_not_marked_partial_at_a_tool_limit(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond
    from tests.integration.test_agent import _evidence_id

    _metadata_corpus(make_pdf, tmp_path)

    def only_new(messages: list[dict[str, Any]]) -> Any:
        key = _evidence_id(messages, "Password Standard", 1)
        return respond(
            (
                "final_answer",
                {
                    "summary": "Passwords do not expire.",
                    "claims": [
                        {"text": "Passwords do not expire.", "evidence_ids": [key], "quote": QUOTE_NEW}
                    ],
                },
            )
        )

    model = ScriptedModel([respond(("search_documents", {"query": "passwords expire prohibited"})), only_new])
    outcome, _ = _run(model, "Do passwords expire?", agent_max_tool_calls=2)
    assert outcome.stop_reason == "answered"
    assert outcome.answer["partial"] is False


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


def test_a_request_to_simplify_the_previous_answer_does_not_search(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(
                (
                    "chat_reply",
                    {
                        "message": (
                            "In simple terms, the assignment is to build an app that finds useful text "
                            "before it answers."
                        )
                    },
                )
            )
        ]
    )
    outcome, events = _run(
        model,
        "Explain that in simpler words",
        ctx_kwargs={"history": [("What is the assignment?", "Build a RAG application over uploaded PDFs.")]},
    )
    assert outcome.stop_reason == "answered"
    assert outcome.totals.tool_calls == 0
    assert not events.of("tool_call")
    assert outcome.answer["summary"].startswith("In simpler terms:")


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


def test_focused_follow_up_reserves_the_final_search_slot_for_an_answer(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    guest = _document_id("01-guest")
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network limits"})),
            # This second search is plausible but redundant. The loop should stop it before consuming the
            # last slot, then force a grounded final_answer from the first result.
            respond(("search_documents", {"query": "guest network policy details"})),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(
        model,
        "What else about the guest network?",
        ctx_kwargs={"history": [("What is the guest limit?", "10 Mbps")], "cited": frozenset({(guest, 1)})},
        agent_max_tool_calls=2,
    )
    assert outcome.stop_reason == "answered" and outcome.totals.tool_calls == 1
    assert events.of("early_stop")


def test_follow_up_duplicate_page_read_finishes_from_existing_evidence(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    """A repeated focused page read should not turn a supported follow-up into a limit failure."""
    from app.llm.client import ScriptedModel, respond

    _load(make_pdf, tmp_path)
    guest = _document_id("01-guest")
    read = {"document_id": guest, "page_start": 1, "page_end": 1}
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "guest network limits"})),
            respond(("read_document_pages", read)),
            respond(("read_document_pages", read)),
            _answer_step("Guest", 1, QUOTE_MBPS),
        ]
    )
    outcome, events = _run(
        model,
        "What is the guest bandwidth?",
        ctx_kwargs={"history": [("q", "a")], "cited": frozenset({(guest, 1)})},
    )
    assert outcome.stop_reason == "answered"
    assert events.of("early_stop")
    assert any(e["status"] == "blocked" for e in events.of("tool_call"))


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


def test_a_long_grounded_default_quote_is_accepted() -> None:
    from app.tools.contracts import AssessQuestionInput

    quote = "A restrictive rule applies to this documented condition. " * 12
    verdict = AssessQuestionInput.model_validate(
        {"answerable": True, "default_reading": "restricted data", "default_quote": quote}
    )
    assert verdict.default_quote == quote


def test_a_long_interpretation_quote_is_accepted() -> None:
    from app.tools.contracts import AssessQuestionInput

    quote = "The policy applies to restricted material " * 12
    verdict = AssessQuestionInput.model_validate(
        {
            "answerable": False,
            "interpretations": [{"label": "Restricted material", "quote": quote}],
        }
    )
    assert verdict.interpretations[0].quote == quote


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


def test_null_text_fields_from_the_judge_do_not_disable_the_check(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_renewal(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "renew account"})),
            _renewal_assessment(facet=None, missing_slot=None, clarification_question=None),
        ]
    )
    outcome, events = _run(model, "How do I renew my account?", agent_assess_ambiguity=True)
    assert outcome.stop_reason == "clarification_needed"  # asked, with a question the code wrote itself
    assert "Student account" in outcome.clarification["question"]
    assert "skipped" not in events.of("assessment")[0]["assessment"]


SCOPE_AND_LEVELS = [
    "1. Scope\n\nThis policy covers the following accounts: the LMS account and the VPN account.\n\n"
    "Level 3 data must be encrypted with AES-128 before storage in any approved system.\n\n"
    "Level 4 data must be encrypted with AES-256 and the keys kept in a hardware module.",
]


def _load_scope_and_levels(make_pdf: Callable[..., Path], tmp_path: Path) -> None:
    from app.ingest.pipeline import ensure_corpus_loaded

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    make_pdf(SCOPE_AND_LEVELS, name="corpus/03-levels.pdf")
    make_pdf(REMOTE, name="corpus/02-remote.pdf")
    clear_caches()
    asyncio.run(ensure_corpus_loaded(corpus))
    clear_caches()


def _kinds(*pairs: tuple[str, str], **fields: Any) -> Any:
    return _assess(
        False,
        answers_differ=True,
        interpretations=[{"label": label, "quote": quote} for label, quote in pairs],
        **fields,
    )


def test_a_list_of_what_exists_is_not_a_set_of_kinds_to_choose_between(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_scope_and_levels(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "accounts scope"})),
            _kinds(
                ("LMS account", "the LMS account and the VPN account"),
                ("VPN account", "This policy covers the following accounts"),
            ),
            respond(("final_answer", {"summary": "The documents do not contain this."})),
        ]
    )
    outcome, events = _run(model, "When is an inactive account suspended?", agent_assess_ambiguity=True)
    assert outcome.stop_reason != "clarification_needed"
    kinds = events.of("assessment")[0]["assessment"]["kinds"]
    assert {k["status"] for k in kinds} <= {"not_about_the_question", "rules_alike", "label_not_in_passage"}


def test_a_number_in_the_question_names_the_kind_it_means(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_scope_and_levels(make_pdf, tmp_path)
    pairs = (
        ("Level 3 data", "Level 3 data must be encrypted with AES-128 before storage"),
        (
            "Level 4 data",
            "Level 4 data must be encrypted with AES-256 and the keys kept in a hardware module",
        ),
    )
    for question, expect_ask in (
        ("How is Level 4 data encrypted?", False),  # the digit names the kind
        ("How is data encrypted?", True),
    ):
        model = ScriptedModel(
            [
                respond(("search_documents", {"query": "data encrypted levels"})),
                _kinds(*pairs),
                respond(("final_answer", {"summary": "The documents do not contain this."})),
            ]
        )
        outcome, events = _run(model, question, agent_assess_ambiguity=True)
        assert (outcome.stop_reason == "clarification_needed") is expect_ask, question
        statuses = {k["label"]: k["status"] for k in events.of("assessment")[0]["assessment"]["kinds"]}
        if expect_ask:
            assert statuses == {"Level 3 data": "verified", "Level 4 data": "verified"}
        else:
            assert statuses["Level 4 data"] == "named_by_user"


def test_the_question_offered_lists_only_the_kinds_that_passed(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel, respond

    _load_scope_and_levels(make_pdf, tmp_path)
    model = ScriptedModel(
        [
            respond(("search_documents", {"query": "data encrypted levels"})),
            _kinds(
                ("Level 3 data", "Level 3 data must be encrypted with AES-128 before storage"),
                (
                    "Level 4 data",
                    "Level 4 data must be encrypted with AES-256 and the keys kept in a hardware module",
                ),
                (
                    "Level 5 data",
                    "Level 5 data must be encrypted with a quantum-safe scheme",
                ),  # not in the results
                clarification_question="Which level: Level 3 data, Level 4 data or Level 5 data?",
            ),
        ]
    )
    outcome, _ = _run(model, "How is data encrypted?", agent_assess_ambiguity=True)
    assert outcome.clarification["options"] == ["Level 3 data", "Level 4 data"]
    assert "Level 5" not in outcome.clarification["question"]
    assert [s["label"] for s in outcome.clarification_sources] == ["Level 3 data", "Level 4 data"]
    assert all(s["page"] == 1 and s["quote"] for s in outcome.clarification_sources)


def test_the_page_behind_the_chosen_option_is_read_before_the_model_starts(
    make_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    from app.llm.client import ScriptedModel
    from app.turns.service import _chosen_source

    _load_scope_and_levels(make_pdf, tmp_path)
    document_id = _document_id("03-levels")
    sources = [
        {"label": "Level 3 data", "document_id": document_id, "page": 1, "quote": "x"},
        {"label": "Level 4 data", "document_id": document_id, "page": 1, "quote": "y"},
    ]
    assert _chosen_source(sources, "Level 4, please") == (document_id, 1)
    assert _chosen_source(sources, "data") is None  # names neither
    assert _chosen_source(sources, "Level 3 or level 4") is None  # names both

    model = ScriptedModel(
        [
            _answer_step(
                "Scope", 1, "Level 4 data must be encrypted with AES-256", "Level 4 data uses AES-256."
            )
        ]
    )
    outcome, events = _run(
        model,
        "Level 4",
        ctx_kwargs={
            "clarification": ("Which level?", "Level 4"),
            "original_question": "How is data encrypted?",
            "preload": (document_id, 1),
        },
    )
    assert events.of("tool_call")[0]["tool"] == "read_document_pages"
    assert outcome.totals.tool_calls == 1 and outcome.totals.model_requests == 1  # no search was needed
    assert outcome.stop_reason == "answered"


def test_judge_listing_more_than_five_readings_is_still_assessed() -> None:
    from app.tools.contracts import AssessQuestionInput

    readings = [{"label": f"Option {i}", "quote": f"Rule number {i} applies."} for i in range(7)]
    parsed = AssessQuestionInput.model_validate({"answerable": False, "interpretations": readings})
    assert len(parsed.interpretations) == 7


def test_a_word_shared_by_some_labels_does_not_count_as_naming_one() -> None:
    from app.agent.loop import AgentRun
    from app.tools.contracts import AssessQuestionInput

    texts = {
        "Home Directories": "Home Directories: quota 50 GB per user.",
        "Project Storage": "Project Storage: quota set per allocation.",
        "Scratch Storage": "Scratch Storage: purged after 60 days.",
    }
    verdict = AssessQuestionInput.model_validate(
        {
            "answerable": False,
            "answers_differ": True,
            "interpretations": [{"label": k, "quote": v} for k, v in texts.items()],
        }
    )
    hits = [{"excerpt": " ".join(texts.values()), "document_id": "d1", "page": 5}]
    run = AgentRun.__new__(AgentRun)
    run.question = "How much storage do I get?"
    broad = run._backed_variants(verdict, hits)
    assert not broad.named and len(broad.options) == 3
    run.question = "How much scratch space do I get?"
    assert run._backed_variants(verdict, hits).named


def test_an_unowned_session_can_be_resumed_from_a_history_list(client: Any) -> None:
    first = client.post("/api/v1/sessions").json()["session_id"]
    second = client.post("/api/v1/sessions").json()["session_id"]
    assert client.cookies["pp_session"] == second
    resumed = client.post(f"/api/v1/sessions/{first}/resume")
    assert resumed.status_code == 200 and client.cookies["pp_session"] == first
    assert client.post(f"/api/v1/sessions/{uuid.uuid4()}/resume").status_code == 404
