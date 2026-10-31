import uuid

import pytest

from app.agent.verifier import EvidenceItem, check_quote, normalize, verify_answer
from app.tools.contracts import DraftClaim, FinalAnswerInput, Notice

DOC = uuid.uuid4()
OTHER = uuid.uuid4()
PAGES = {
    (DOC, 1): "The guest network is limited to 10 Mbps download\nand 2 Mbps upload for unregistered devices.",
    (OTHER, 2): "Passwords must be changed every 90 days.",
}
LEDGER = {"E1": EvidenceItem("E1", DOC, "Acceptable Use", 1), "E2": EvidenceItem("E2", OTHER, "Passwords", 2)}


async def page_text(document_id: uuid.UUID, page: int) -> str | None:
    return PAGES.get((document_id, page))


def test_normalize_ignores_case_whitespace_and_punctuation() -> None:
    assert normalize("  The Guest-Network,\n limit! ") == "the guest network limit"


@pytest.mark.parametrize(
    ("quote", "expected"),
    [
        ("limited to 10 Mbps download and 2 Mbps upload", "exact_quote"),
        ("LIMITED TO 10 mbps download   and 2 Mbps upload", "exact_quote"),
        ("the network is limited to 10 Mbps download and 2 Mbps upload for devices", "overlap"),
        ("limited to 100 Mbps", "failed"),
        ("", "failed"),
    ],
)
def test_check_quote(quote: str, expected: str) -> None:
    assert check_quote(quote, PAGES[(DOC, 1)]) == expected


async def test_verified_claims_get_numbered_citations() -> None:
    draft = FinalAnswerInput(
        summary="Guests get 10 Mbps. Passwords rotate every 90 days.",
        claims=[
            DraftClaim(text="Guest download is 10 Mbps.", evidence_ids=["E1"], quote="10 Mbps download"),
            DraftClaim(text="Passwords rotate every 90 days.", evidence_ids=["E2"], quote="every 90 days"),
            DraftClaim(text="Uploads are 2 Mbps.", evidence_ids=["E1"], quote="2 Mbps upload"),
        ],
    )
    result = await verify_answer(draft, LEDGER, page_text)
    assert result.ok
    answer = result.answer
    assert [c["index"] for c in answer["citations"]] == [1, 2]
    assert answer["claims"][0]["citation_indexes"] == [1]
    assert answer["claims"][2]["citation_indexes"] == [1]  # same page reuses the same citation
    assert answer["stop_reason"] == "answered" and answer["unverified_claims"] == []


async def test_unsupported_and_unknown_evidence_are_rejected() -> None:
    draft = FinalAnswerInput(
        summary="x",
        claims=[
            DraftClaim(text="Wrong quote.", evidence_ids=["E1"], quote="limited to 500 Mbps"),
            DraftClaim(text="Never seen.", evidence_ids=["E9"], quote="anything"),
            DraftClaim(text="Good.", evidence_ids=["E2"], quote="every 90 days"),
        ],
    )
    result = await verify_answer(draft, LEDGER, page_text)
    assert not result.ok and len(result.failures) == 2
    assert [c["text"] for c in result.answer["claims"]] == ["Good."]
    assert result.answer["unverified_claims"] == ["Wrong quote.", "Never seen."]
    assert result.answer["summary"] == "Good."
    assert result.answer["partial"] is False


async def test_no_supported_claims_means_insufficient_evidence() -> None:
    draft = FinalAnswerInput(
        summary="The documents do not cover that.",
        notices=[Notice(kind="missing_evidence", text="Nothing about home internet reimbursement.")],
    )
    result = await verify_answer(draft, LEDGER, page_text)
    assert result.ok and result.answer["stop_reason"] == "insufficient_evidence"
    assert result.answer["notices"][0]["kind"] == "missing_evidence"


def test_locate_quote_returns_the_literal_page_span() -> None:
    from app.agent.verifier import locate_quote

    page = (
        "Section 3.\nUnregistered guest devices are limited to 10 Mbps\n"
        "download and 2 Mbps upload. Other text."
    )
    wrapped = '"Unregistered guest devices are limited to 10 Mbps download and 2 Mbps upload"'
    span = locate_quote(wrapped, page)
    assert span == "Unregistered guest devices are limited to 10 Mbps\ndownload and 2 Mbps upload"
    assert " ".join(span.casefold().split()) in " ".join(page.casefold().split())
    assert locate_quote("limited to 500 Mbps", page) is None
    assert locate_quote("", page) is None


def test_nearly_exact_quotes_snap_to_the_literal_page_sentence() -> None:
    from app.agent.verifier import nearest_span

    page = (
        "Header line.\nRequests for VPN split-tunnel exceptions must be submitted through the IT Governance "
        "portal and require written approval from the Chief Information Security Officer. Other sentence."
    )
    paraphrased = (
        "Requests for VPN split-tunnel exceptions must be submitted through the IT Governance portal "
        "and require approval from the Chief Information Security Officer"
    )
    span = nearest_span(paraphrased, page)
    assert span is not None and span in page and "written approval" in span
    assert nearest_span("Completely unrelated sentence about parking permits today", page) is None
    assert nearest_span("too short", page) is None


def test_evidence_ids_are_removed_from_the_text_people_read() -> None:
    from app.agent.verifier import strip_evidence_ids

    assert strip_evidence_ids("MFA is required (E2). Details (Remote Work Standard, p. 2, E4).") == (
        "MFA is required. Details (Remote Work Standard, p. 2)."
    )
    assert strip_evidence_ids("Both apply [E1, E3] to VPN.") == "Both apply to VPN."
    assert strip_evidence_ids("Version E2E is unaffected") == "Version E2E is unaffected"


def test_a_slightly_long_field_is_shortened_instead_of_failing_the_turn() -> None:
    from app.agent.verifier import sanitize_final_answer
    from app.tools.contracts import FinalAnswerInput

    long_quote = "The most common security practices include " + "careful " * 80  # over 400 characters
    args = sanitize_final_answer(
        {
            "summary": "x" * 2000,
            "claims": [
                {"text": "y" * 900, "evidence_ids": ["E1", "E2", "E3", "E4", "E5"], "quote": long_quote}
                for _ in range(15)
            ],
            "notices": [{"kind": "partial", "text": "z" * 700}],
        }
    )
    draft = FinalAnswerInput.model_validate(args)  # must validate: this used to be an "error" turn
    assert len(draft.summary) <= 1500 and len(draft.claims) == 12
    claim = draft.claims[0]
    assert len(claim.quote) <= 400 and long_quote.startswith(claim.quote)  # still a literal prefix
    assert len(claim.text) <= 600 and len(claim.evidence_ids) == 4 and len(draft.notices[0].text) <= 500


def test_unknown_fields_do_not_fail_the_turn_and_a_stray_missing_evidence_becomes_a_notice() -> None:
    from app.agent.verifier import sanitize_final_answer
    from app.tools.contracts import FinalAnswerInput

    draft = FinalAnswerInput.model_validate(
        sanitize_final_answer(
            {
                "summary": "The documents do not cover apples.",
                "claims": [],
                "missing_evidence": {"text": "Nothing about apples.", "evidence_ids": []},
                "confidence": 0.2,
            }
        )
    )
    assert draft.notices[0].kind == "missing_evidence" and draft.notices[0].text == "Nothing about apples."
    odd = FinalAnswerInput.model_validate(
        sanitize_final_answer(
            {
                "summary": "s",
                "claims": [{"text": "t", "evidence_ids": ["E1"], "quote": "q", "extra": 1}],
                "notices": [{"kind": "made_up_kind", "text": "n", "oops": True}],
            }
        )
    )
    assert odd.notices[0].kind == "partial" and len(odd.claims) == 1


@pytest.mark.parametrize(
    ("figure", "text", "expected"),
    [
        ("10", "limited to 10 Mbps", True),
        ("20", "10 Mbps in the 2024 standard", False),  # "20" is inside "2024"
        ("30", "retained for 130 days", False),  # "30" is inside "130"
        ("10", "a rate of 10.5 Mbps", False),  # "10" is not "10.5"
        ("10.5", "a rate of 10.5 Mbps", True),
        ("1,000", "up to 1000 files", True),  # separators are ignored
        ("1000", "up to 1,000 files", True),
        ("90", "valid for ninety (90) days", True),
    ],
)
def test_figures_match_whole_numbers_only(figure: str, text: str, expected: bool) -> None:
    from app.agent.verifier import figure_in_text

    assert figure_in_text(figure, text) is expected


async def test_a_claim_with_a_figure_that_is_only_part_of_another_number_is_rejected() -> None:
    draft = FinalAnswerInput(
        summary="Guests get 2 Mbps.",
        claims=[DraftClaim(text="Guest upload is 20 Mbps.", evidence_ids=["E1"], quote="2 Mbps upload")],
    )
    result = await verify_answer(draft, LEDGER, page_text)
    assert result.answer["claims"] == [] and result.answer["stop_reason"] == "insufficient_evidence"
    assert not result.ok


async def test_an_abstention_never_keeps_the_models_affirmative_summary() -> None:
    from app.agent.loop import ABSTAIN_TEXT, AgentRun

    draft = FinalAnswerInput(
        summary="Guests get unlimited bandwidth and 90 days of access.",
        claims=[DraftClaim(text="Guests get 999 Mbps.", evidence_ids=["E1"], quote="2 Mbps upload")],
    )
    verified = await verify_answer(draft, LEDGER, page_text)
    run = AgentRun.__new__(AgentRun)
    answer = await run._normalize(verified.answer)
    assert answer["stop_reason"] == "insufficient_evidence"
    assert answer["summary"] == ABSTAIN_TEXT and "unlimited" not in answer["summary"]
    assert any(n["kind"] == "missing_evidence" for n in answer["notices"])


async def test_a_summary_with_only_rejected_sentences_falls_back_to_the_verified_claims() -> None:
    from app.agent.loop import AgentRun

    draft = FinalAnswerInput(
        summary="Guests get 999 Mbps.",
        claims=[DraftClaim(text="Guest download is 10 Mbps.", evidence_ids=["E1"], quote="10 Mbps download")],
    )
    verified = await verify_answer(draft, LEDGER, page_text)
    run = AgentRun.__new__(AgentRun)
    run.page_text = page_text  # type: ignore[method-assign]
    answer = await run._verify_summary(verified.answer)
    assert "999" not in answer["summary"] and "10 Mbps" in answer["summary"]
